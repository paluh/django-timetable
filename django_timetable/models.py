from dateutil import rrule
from django.conf import settings

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from .abstract import AbstractMixin
from .fields import RruleField

class OccurrenceSeriesFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'))
    end = models.DateTimeField(_('end'),help_text=_('The end time must be later than the start time.'))
    end_recurring_period = models.DateTimeField(_('end recurring period'), blank=True, null=True,
            help_text=_('This date is ignored for one time only events.'))

    class Meta:
        abstract = True

    #you can define rrules consts by:
    #  * creating tuple which contains known interval value name from rrule module,
    #       for example: rrule.WEEKLY -> ('WEEKLY', '<display value>')
    #  * creating tuple of three values ('<db_const>', '<display value>', <dict of dateutil.rrule.rrule init parameters>),
    #       for example: ('EVERY_TWO_WEEKS', '<display value>', {'freq': rrule.WEEKLY, 'interval': 2})
    RULES = (
        ('ONCE', _('Once')),
        ('YEARLY', _('Yearly')),
        ('MONTHLY', _('Monthly')),
        ('WEEKLY', _('Weekly')),
        #example of more complicated rule
        ('EVERY_TWO_WEEKS', _('Every two weeks'), {'freq': rrule.WEEKLY, 'interval': 2}),
        ('DAILY', _('Daily')),
        ('HOURLY', _('Hourly')),
        ('MINUTELY', _('Minutely')),
        ('SECONDLY', _('Secondly'))
    )
    @classmethod
    def contribute(cls, rule_choices=RULES, default_rule=0):
        rule_choices = rule_choices or cls.RULES
        max_length = max([len(rule_choice[0]) for rule_choice in rule_choices])
        fields = {
            'rule': RruleField(choices=rule_choices,
                max_length=max_length, default=rule_choices[default_rule][0])
        }
        return fields

    def get_occurrences(self, start=None, end=None, commit=False, defaults=None):
        defaults = defaults or {}
        start, end = start or self.start, end or self.end_recurring_period or self.end
        #FIXME: dateutil rrule implemetation ignores microseconds
        start, end = start.replace(microsecond=0), end.replace(microsecond=0)
        delta = self.end - self.start
        if self.rule != None:
            starts = self.rule(start, end)
        else:
            starts = [self.start]
        #this prevents 'too many SQL variables' raised by sqlite
        count = 0
        for slice in map(None, *(iter(starts),) * getattr(settings, 'MAX_SQL_VARS', 500)):
            count += self.occurrences.filter(original_start__in=slice).count()
        result = list(self.occurrences.filter(start__gte=start, start__lt=end))
        if count != len(starts):
            db_starts = []
            for slice in map(None, *(iter(starts),) * getattr(settings, 'MAX_SQL_VARS', 500)):
                db_starts.extend(self.occurrences.filter(original_start__in=slice).values_list('original_start', flat=True))
            missed = filter(lambda start: start not in db_starts, starts)
            for s in missed:
                result.append(self.occurrences.model(event=self, original_start=s, start=s, original_end=s+delta, end=s+delta, **defaults))
            if commit:
                for occurrence in result:
                    occurrence.save()
        result.sort(lambda o1, o2: cmp(o1.start, o2.start))
        return result

    def clean(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError("Start value can't be greater then end value.")
        if self.end_recurring_period is None and self.rule != None:
            raise ValidationError("You have to pass end period for recurring series!")

class OccurrenceFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'), blank=True)
    end = models.DateTimeField(_('end'), blank=True)
    original_start = models.DateTimeField(_('original start'))
    original_end = models.DateTimeField(_('original end'))

    class Meta:
        abstract = True

    @classmethod
    def contribute(cls, event):
        return {'event': models.ForeignKey(event, related_name='occurrences')}

    def clean(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError("Start value can't be greater then end value!")

    def save(self, *args, **kwargs):
        if not self.start:
            self.start = self.original_start
        if not self.end:
            self.end = self.original_start
        models.Model.save(self, *args, **kwargs)
