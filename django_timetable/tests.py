import datetime
from dateutil import rrule

from django.core.exceptions import ValidationError
from django import forms
from django.db import models
from django.test import TestCase

from .models import OccurrenceSeriesFactory, OccurrenceFactory
from .fields import RruleField

RRULES_CHOICES = (
    ('ONCE', 'once',),
    ('HOURLY', 'hourly'),
    ('DAILY', 'daily',),
    ('WEEKLY', 'weekly'),
    ('EVERY_TWO_WEEKS', 'every two weeks', {'freq': rrule.WEEKLY, 'interval': 2}),
)

class OccurrenceSeries(OccurrenceSeriesFactory.construct(rule_choices=RRULES_CHOICES)):
    pass

class Occurrence(OccurrenceFactory.construct(event=OccurrenceSeries)):
    name = models.CharField(max_length=128, blank=True)

    def __unicode__(self):
        return '%s (%s - %s)' % (self.name or self.event.name, self.start, self.end)

#models for testing defaults values passing
class OccurrenceSeriesWithRequiredFields(OccurrenceSeriesFactory.construct()):
    pass
class OccurrenceWithRequiredField(OccurrenceFactory.construct(event=OccurrenceSeriesWithRequiredFields)):
    required_value = models.IntegerField()

    def __unicode__(self):
        return '%s (%s - %s)' % (self.name or self.event.name, self.start, self.end)

class Fields(TestCase):
    def test_custom_rrule_value(self):
        now = datetime.datetime.now()
        o = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='EVERY_TWO_WEEKS')
        self.assertEqual(o.rule, RruleField.RruleWrapper(freq=rrule.WEEKLY, interval=2))

    def test_once_rrule_value(self):
        o = OccurrenceSeries(rule='ONCE')
        self.assertEqual(o.rule, None)

    def test_modelform_validation_for_rrule_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeries
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                'end': start+datetime.timedelta(hours=1),
                'end_recurring_period': start+datetime.timedelta(weeks=1),
                'rule': 'WEEKLY'
        })
        self.assertTrue(form.is_valid())

    def test_modelform_save_for_rrule_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeries
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                'end': start+datetime.timedelta(hours=1),
                'end_recurring_period': start+datetime.timedelta(weeks=1),
                'rule': 'WEEKLY'
        })
        form.is_valid()
        series = form.save()
        series = OccurrenceSeries.objects.get(id=series.id)
        self.assertEqual(series.rule.params['freq'], rrule.WEEKLY)

    def test_modelform_save_for_rrule_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeries
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                'end': start+datetime.timedelta(hours=1),
                'end_recurring_period': start+datetime.timedelta(weeks=1),
                'rule': 'UNKNOWN'
        })
        self.assertFalse(form.is_valid())
        self.assertTrue('rule' in form.errors)

class Models(TestCase):
    def test_get_occurrences_saves_proper_objects_number(self):
        start = datetime.datetime.now().replace(microsecond=0)
        end = start+datetime.timedelta(hours=1)
        end_recurring_period=start+datetime.timedelta(weeks=5)

        event = OccurrenceSeries.objects.create(start=start, end=end, end_recurring_period=end_recurring_period, rule='WEEKLY')
        occurrences = event.get_occurrences(commit=False)
        self.assertEqual(len(occurrences), len(list(rrule.rrule(dtstart=start, until=end_recurring_period, freq=rrule.WEEKLY))))

    def test_get_occurrences_returns_one_object_for_onetime_rule(self):
        now = datetime.datetime.now()
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='ONCE')
        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end, commit=True)
        self.assertEqual(event.occurrences.count(), 1)

    def test_get_occurrences_saves_objects_on_demand(self):
        now = datetime.datetime.now()
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')

        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end)

        self.assertEqual(event.occurrences.count(), 0)
        occurrences = event.get_occurrences(now, end, commit=True)
        self.assertEqual(event.occurrences.count(), len(occurrences))

    def test_get_occurrences_passes_defaults_to_generated_occurrences(self):
        now = datetime.datetime.now()
        event = OccurrenceSeriesWithRequiredFields.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=1), rule='DAILY')

        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(commit=True, defaults={'required_value': 1})

    def test_get_occurrences_returns_proper_number_when_some_tracks_already_exists(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')

        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(hours=8)
        event.get_occurrences(now, end, commit=True)

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end)
        self.assertEqual(len(occurrences),
                len(list(rrule.rrule(dtstart=now, until=end, freq=rrule.HOURLY))))

    def test_get_occurrences_returns_proper_number_for_custom_rrule(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='EVERY_TWO_WEEKS')

        end = now+datetime.timedelta(weeks=4)
        event.get_occurrences(now, end)

        occurrences = event.get_occurrences(now, end)
        self.assertEqual(len(occurrences),
                len(list(rrule.rrule(dtstart=now, until=end, freq=rrule.WEEKLY, interval=2))))

    def test_save_fails_when_start_is_greater_then_end(self):
        now = datetime.datetime.now()
        event = OccurrenceSeries(start=now+datetime.timedelta(hours=1), end=now,
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')
        self.assertRaises(ValidationError, lambda: event.full_clean())

