from django.conf import settings

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .abstract import AbstractMixin
from .fields import RruleField


class OccurrenceSeriesFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'))
    end = models.DateTimeField(_('end'))
    end_recurring_period = models.DateTimeField(
        _('end recurring period'), blank=True, null=True,
        help_text=_('This date is ignored for one time only events.')
    )

    class Meta:
        abstract = True

    #for examples of rule choices look into fields.py
    @classmethod
    def contribute(cls, rrule_kwargs=None):
        defaults = {'verbose_name': _('Rule')}
        rrule_kwargs = defaults.update(rrule_kwargs or {})
        fields = {'rule': RruleField(**rrule_kwargs)}
        return fields

    def get_occurrences(self, start=None, end=None,
                                commit=False, defaults=None):
        defaults = defaults or {}
        start, end = start or self.start, end \
                or self.end_recurring_period or self.end
        #FIXME: dateutil rrule implemetation ignores microseconds
        start, end = start.replace(microsecond=0), end.replace(microsecond=0)
        delta = self.end - self.start
        if self.rule != None:
            starts = list(self.rule(dtstart=start, until=end))
        else:
            starts = [self.start]
        #this prevents 'too many SQL variables' raised by sqlite
        count = 0
        max_sql_vars = getattr(settings, 'MAX_SQL_VARS', 500)
        for slice in map(None, *(iter(starts),) * max_sql_vars):
            count += self.occurrences.filter(original_start__in=slice).count()
        result = list(self.occurrences.filter(start__gte=start, start__lt=end))
        if count != len(starts):
            db_starts = []
            for slice in map(None, *(iter(starts),) * max_sql_vars):
                db_starts.extend(self.occurrences \
                        .filter(original_start__in=slice) \
                        .values_list('original_start', flat=True))
            missing = filter(lambda start: start not in db_starts, starts)
            for s in missing:
                result.append(self.occurrences.model(
                    event=self,
                    original_start=s, start=s,
                    original_end=s+delta, end=s+delta, **defaults)
                )
            if commit:
                for occurrence in result:
                    occurrence.save()
        result.sort(lambda o1, o2: cmp(o1.start, o2.start))
        return result

    def clean(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError(_("Start value can't be greater then end value."))
        if self.end_recurring_period is None and self.rule != None:
            raise ValidationError(_("You have to pass end period for recurring series."))
        if self.start and self.end_recurring_period and self.start > self.end_recurring_period:
            raise ValidationError(_("End recurring period can't be earlier than series start."))

class OccurrenceFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'), blank=True)
    end = models.DateTimeField(_('end'), blank=True)
    original_start = models.DateTimeField(_('original start'), editable=False)
    original_end = models.DateTimeField(_('original end'), editable=False)

    class Meta:
        abstract = True

    @classmethod
    def contribute(cls, event):
        return {
            'event': models.ForeignKey(
                event, related_name='occurrences',
                editable=False
            )
        }

    def clean(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError(_("Start value can't be greater then end value!"))

    def save(self, *args, **kwargs):
        if not self.start:
            self.start = self.original_start
        if not self.end:
            self.end = self.original_start
        models.Model.save(self, *args, **kwargs)
