from dateutil import rrule
from django.conf import settings

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from .abstraction import AbstractModelFactory, AbstractMixin

class RruleChoice(tuple):
    _rr_params_cache = {}
    def __new__(cls, value, display, rr_params):
        instance = super(RruleChoice, cls).__new__(cls, (value, display))
        cls._rr_params_cache[value] = rr_params
        return instance

    @classmethod
    def get_params(cls, value):
        return cls._rr_params_cache[value]

class EventFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'))
    end = models.DateTimeField(_('end'),help_text=_('The end time must be later than the start time.'))
    end_recurring_period = models.DateTimeField(_('end recurring period'), help_text=_('This date is ignored for one time only events.'))

    RULES = (
        ('ONCE', _('Once')),
        ('YEARLY', _('Yearly')),
        ('MONTHLY', _('Monthly')),
        ('WEEKLY', _('Weekly')),
        #example of more complicated rrule
        RruleChoice('EVERY_TWO_WEEKS', _('Every two weeks'),
            rr_params={'freq': rrule.WEEKLY, 'interval':2}),
        ('DAILY', _('Daily')),
        ('HOURLY', _('Hourly')),
        ('MINUTELY', _('Minutely')),
        ('SECONDLY', _('Secondly'))
    )
    class Meta:
        abstract = True

    @classmethod
    def contribute(cls, rule_choices=RULES, default_rule=0):
        max_length = max([len(rule_choice[0]) for rule_choice in rule_choices])
        fields = {
            'rule': models.CharField(choices=rule_choices,
                max_length=max_length, default=rule_choices[default_rule][0])
        }
        return fields

    def get_occurrences(self, start, end, commit=False):
        #dateutil rrule implemetation ignores microseconds
        start, end = start.replace(microsecond=0), end.replace(microsecond=0)
        delta = self.end - self.start
        if self.rule != 'ONCE':
            rule = self.get_rrule()
            starts = rule.between(start, end, inc=True)
            #this prevents 'too many SQL variables' raised by sqlite
            count = 0
            for slice in map(None, *(iter(starts),) * getattr(settings, 'MAX_SQL_VARS', 500)):
                count += self.occurrences.filter(original_start__in=slice).count()
            result = list(self.occurrences.filter(start__gte=start, start__lt=end, cancelled=False))
            if count != len(starts):
                db_starts = []
                for slice in map(None, *(iter(starts),) * getattr(settings, 'MAX_SQL_VARS', 500)):
                    db_starts.extend(self.occurrences.filter(original_start__in=slice).values_list('original_start', flat=True))
                missed = filter(lambda start: start not in db_starts, starts)
                for s in missed:
                    result.append(self.occurrences.model(event=self, original_start=s, start=s, original_end=s+delta, end=s+delta))
                if commit:
                    for occurrence in result:
                        occurrence.save()
            result.sort(lambda o1, o2: cmp(o1.start, o2.start))
        else:
            try:
                result = [self.occurrences.get()]
            except self.occurrences.model.DoesNotExist:
                occurrence = self.occurrences.model(event=self, original_start=start, start=start, original_end=start+delta, end=start+delta)
                if commit:
                    occurrence.save()
                result = [occurrence]
        return result

    def get_rrule(self):
        if hasattr(rrule, self.rule):
            frequency = getattr(rrule, self.rule)
            return rrule.rrule(frequency, dtstart=self.start)

        params = RruleChoice.get_params(self.rule)
        return rrule.rrule(dtstart=self.start, **params)

    def clean(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError("Start value can't be greater then end value!")

    def save(self, *args, **kwargs):
        models.Model.save(self, *args, **kwargs)

class OccurrenceFactory(models.Model, AbstractMixin):
    start = models.DateTimeField(_('start'), blank=True)
    end = models.DateTimeField(_('end'), blank=True)
    cancelled = models.BooleanField(_('cancelled'), default=False)
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
