import datetime
from dateutil import rrule

from django.core.exceptions import ValidationError
from django import forms
from django.db import models
from django.test import TestCase

from .models import OccurrenceSeriesFactory, OccurrenceFactory
from .fields import RruleField, ComplexRruleField

class OccurrenceSeriesWithRruleField(OccurrenceSeriesFactory.construct(rrule=RruleField(rrule.HOURLY,
                                                                                       blank=True, null=True))):
    pass


class Occurrence(OccurrenceFactory.construct(event=OccurrenceSeriesWithRruleField)):
    # required field
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return '%s (%s - %s)' % (self.name or '[noname]', self.start, self.end)



class RruleFieldTest(TestCase):
    def test_returned_rrule_function(self):
        now = datetime.datetime.now()
        o = OccurrenceSeriesWithRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
                                                          end_recurring_period=now+datetime.timedelta(weeks=54),
                                                          rule=24*7*2)
        self.assertEqual(list(o.rule(period_start=o.start, period_end=o.end_recurring_period)),
                        list(rrule.rrule(dtstart=o.start, until=o.end_recurring_period,
                                          freq=rrule.WEEKLY, interval=2)))

    def test_once_rrule_value(self):
        o = OccurrenceSeriesWithRruleField(rule=None)
        self.assertEqual(o.rule, None)


    def test_modelform_save_for_non_empty_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeriesWithRruleField
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                'end': start+datetime.timedelta(hours=1),
                'end_recurring_period': start+datetime.timedelta(weeks=1),
                'rule': '1'
        })
        form.is_valid()
        self.assertTrue(form.is_valid())
        series = form.save()
        series = OccurrenceSeriesWithRruleField.objects.get(id=series.id)
        self.assertEqual(series.rule.interval, 1)


COMPLEX_RRULES_CHOICES = (
    ('', 'once',),
    ('HOURLY', 'hourly'),
    ('DAILY', 'daily',),
    ('WEEKLY', 'weekly'),
    ('EVERY_TWO_WEEKS', 'every two weeks', {'freq': rrule.WEEKLY,
                                            'interval': 2}),
    ('LAST_DAY_OF_MONTH', 'last day of month', {'freq': rrule.MONTHLY,
                                                'bymonthday':-1})
)

class OccurrenceSeriesWithComplexRruleField(OccurrenceSeriesFactory.construct(rrule=ComplexRruleField(rrule.HOURLY,
                                                                              choices=COMPLEX_RRULES_CHOICES,
                                                                              blank=True, null=True))):
    pass


class OccurrenceWithComplexRruleField(OccurrenceFactory.construct(event=OccurrenceSeriesWithComplexRruleField)):
    name = models.CharField(max_length=128, blank=True)

    def __unicode__(self):
        return '%s (%s - %s)' % (self.name or '[noname]', self.start, self.end)


CUSTOM_DISPLAY = u'custom display'
field_with_custom_blank = ComplexRruleField(choices=(('', CUSTOM_DISPLAY),
                                                     ('WEEKLY', 'weekly')))
class OccurrenceSeriesWithComplexRruleFieldAndCustomBlank(OccurrenceSeriesFactory.construct(rrule=field_with_custom_blank)):
    pass


class ComplexRruleFieldTest(TestCase):
    def test_custom_rrule_value(self):
        now = datetime.datetime.now()
        o = OccurrenceSeriesWithComplexRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
                                                                 end_recurring_period=now+datetime.timedelta(weeks=54),
                                                                 rule='EVERY_TWO_WEEKS')
        self.assertEqual(list(o.rule(dtstart=o.start, until=o.end_recurring_period)),
                         list(rrule.rrule(dtstart=o.start, until=o.end_recurring_period,
                                          freq=rrule.WEEKLY, interval=2)))

    def test_once_rrule_value(self):
        o = OccurrenceSeriesWithComplexRruleField(rule='')
        self.assertEqual(o.rule, None)

    def test_blank_choice_with_custom_display(self):
        s = OccurrenceSeriesWithComplexRruleFieldAndCustomBlank()
        s.rule = ''
        self.assertEqual(len(s._meta.get_field('rule').get_choices()), 2)
        self.assertTrue(s._meta.get_field('rule').blank)
        self.assertTrue(CUSTOM_DISPLAY in zip(*s._meta.get_field('rule').get_choices())[1])

    def test_modelform_with_custom_blank_display_validation(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeriesWithComplexRruleFieldAndCustomBlank
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                                          'end': start+datetime.timedelta(hours=1),
                                          'end_recurring_period': start+datetime.timedelta(weeks=1),
                                          'rule': ''})
        form.is_valid()
        series = form.save(commit=False)
        self.assertEqual(series.rule, None)

    def test_modelform_save_for_empty_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeriesWithComplexRruleField
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                'end': start+datetime.timedelta(hours=1),
                'end_recurring_period': start+datetime.timedelta(weeks=1),
                'rule': ''
        })
        self.assertTrue(form.is_valid())
        form.is_valid()
        series = form.save()
        self.assertEqual(series.rule, None)
        self.assertEqual(len(series.get_occurrences()), 1)

    def test_modelform_save_for_non_empty_value(self):
        class OccurrenceSeriesForm(forms.ModelForm):
            class Meta:
                model = OccurrenceSeriesWithComplexRruleField
        start = datetime.datetime.now()
        form = OccurrenceSeriesForm(data={'start': start,
                                          'end': start+datetime.timedelta(hours=1),
                                          'end_recurring_period': start+datetime.timedelta(weeks=1),
                                          'rule': 'EVERY_TWO_WEEKS'})
        self.assertTrue(form.is_valid())
        series = form.save()
        series = OccurrenceSeriesWithComplexRruleField.objects.get(id=series.id)
        self.assertEqual(series.rule.name, 'EVERY_TWO_WEEKS')


class Models(TestCase):
    def test_get_occurrences_saves_proper_objects_number(self):
        start = datetime.datetime.now().replace(microsecond=0)
        end = start+datetime.timedelta(hours=1)
        end_recurring_period=start+datetime.timedelta(weeks=5)

        event = OccurrenceSeriesWithRruleField.objects.create(start=start, end=end,
                                                end_recurring_period=end_recurring_period,
                                                rule=24*7)
        occurrences = event.get_occurrences(commit=False)
        self.assertEqual(len(occurrences), len(list(rrule.rrule(dtstart=start,
                                                                until=end_recurring_period,
                                                                freq=rrule.WEEKLY))))

    def test_get_occurrences_returns_one_object_for_onetime_rule(self):
        now = datetime.datetime.now()
        event = OccurrenceSeriesWithRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule=None)
        end = now+datetime.timedelta(days=1)
        event.get_occurrences(period_start=now, period_end=end, commit=True)
        self.assertEqual(event.occurrences.count(), 1)

    def test_get_occurrences_saves_objects_on_demand(self):
        now = datetime.datetime.now()
        event = OccurrenceSeriesWithRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
                                                end_recurring_period=now+datetime.timedelta(weeks=54),
                                                rule=1)

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(period_start=now, period_end=end)

        self.assertEqual(event.occurrences.count(), 0)
        occurrences = event.get_occurrences(period_start=now, period_end=end, commit=True)
        self.assertEqual(event.occurrences.count(), len(occurrences))

    def test_get_occurrences_passes_defaults_to_generated_occurrences(self):
        now = datetime.datetime.now()
        event = OccurrenceSeriesWithRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
                                                              end_recurring_period=now+datetime.timedelta(weeks=1),
                                                              rule=24)

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(period_start=now, period_end=end, commit=True,
                                            defaults={'name': 'name'})

        self.assertTrue(all(o.name == 'name' for o in occurrences))

    def test_get_occurrences_returns_proper_number_when_some_occurrencies_already_exists(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = OccurrenceSeriesWithRruleField.objects.create(start=now, end=now+datetime.timedelta(hours=1),
                                                end_recurring_period=now+datetime.timedelta(weeks=54),
                                                rule=1)

        rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(hours=8)
        event.get_occurrences(period_start=now, period_end=end, commit=True)

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(period_start=now, period_end=end)
        self.assertEqual(len(occurrences),
                         len(list(rrule.rrule(dtstart=now, until=end, freq=rrule.HOURLY))))

    def test_save_fails_when_start_is_greater_then_end(self):
        now = datetime.datetime.now()
        event = OccurrenceSeriesWithRruleField(start=now+datetime.timedelta(hours=1), end=now,
                                 end_recurring_period=now+datetime.timedelta(weeks=54),
                                 rule=1)
        self.assertRaises(ValidationError, lambda: event.full_clean())

    def test_second_get_occurrences_call_with_commit_false_returns_correct_occurrences(self):
        # regression test
        start = datetime.datetime.now() + datetime.timedelta(minutes=5)
        end_recurring_period = start + datetime.timedelta(hours=1)
        event = OccurrenceSeriesWithRruleField.objects.create(start=start, end=start,
                                                              end_recurring_period=end_recurring_period,
                                                              rule=1)
        occurrences_1 = event.get_occurrences(period_start=start, period_end=end_recurring_period, commit=True)
        occurrences_2 = event.get_occurrences(period_start=start, period_end=end_recurring_period, commit=False)
        self.assertEqual(len(occurrences_1), len(occurrences_2))
        self.assertEqual(occurrences_1, occurrences_2)

    def test_second_get_occurrences_call_with_commit_true_returns_correct_occurrences(self):
        # regression test
        start = datetime.datetime.now() + datetime.timedelta(minutes=5)
        end_recurring_period = start + datetime.timedelta(hours=4)
        event = OccurrenceSeriesWithRruleField.objects.create(start=start, end=start,
                                                              end_recurring_period=end_recurring_period,
                                                              rule=1)
        occurrences_1 = event.get_occurrences(period_start=start, period_end=end_recurring_period, commit=True)
        # this call should not change anything
        event.get_occurrences(period_start=start+datetime.timedelta(hours=2),
                              period_end=end_recurring_period, commit=True)
        occurrences_3 = event.get_occurrences(period_start=start,
                                              period_end=end_recurring_period, commit=False)
        self.assertEqual(len(occurrences_1), len(occurrences_3))
        self.assertEqual(occurrences_1, occurrences_3)

