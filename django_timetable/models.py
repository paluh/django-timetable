from dateutil import rrule

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .abstract import AbstractMixin


class OccurrenceSeriesFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'))
    end = models.DateTimeField(_('end'))
    end_recurring_period = models.DateTimeField(
        _('end recurring period'), blank=True, null=True,
        help_text=_('This date is ignored for one time only events.')
    )

    class Meta:
        abstract = True
        ordering = ('start',)

    @classmethod
    def contribute(cls, rrule=rrule):
        fields = {'rule': rrule}
        return fields

    def _get_missing_occurrences(self, all_occurrences,
                                 existing_occurrences, **defaults):
        result = []
        existing_occurrences = set(existing_occurrences)
        missing = filter(lambda start: start not in existing_occurrences,
                         all_occurrences)
        delta = self.end - self.start
        for s in missing:
            result.append(self.occurrences.model(
                event=self,
                original_start=s, start=s,
                original_end=s+delta, end=s+delta, **defaults)
            )
        return result

    def get_occurrences(self, period_start=None, period_end=None,
                        commit=False, defaults=None, queryset=None):
        defaults = defaults or {}
        queryset = queryset or self.occurrences.all()

        # dateutil ignores microseconds
        start = self.start.replace(microsecond=0)
        period_start = (period_start or self.start).replace(microsecond=0)
        period_end = (period_end or self.end_recurring_period or self.end).replace(microsecond=0)

        if self.rule != None:
            starts = list(self.rule(period_start=start,
                                    period_end=period_end))
            starts = [d for d in starts if d >= period_start]
        else:
            starts = [start]
        result = list(queryset.filter(original_start__lte=period_end,
                                      original_end__gte=period_start))
        if len(result) != len(starts):
            existing = queryset.filter(original_start__lte=period_end,
                                       original_end__gte=period_start).values_list('original_start',
                                                                                   flat=True)
            result.extend(self._get_missing_occurrences(starts, existing, **defaults))
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
        ordering = ('start',)

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
