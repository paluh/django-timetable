import datetime
from dateutil import rrule

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models
from django.test import TestCase

from .models import SequentialOccurrenceSeriesFactory, SequentialOccurrenceFactory

RRULES_CHOICES = (
    ('ONCE', 'once',),
    ('HOURLY', 'hourly'),
    ('DAILY', 'daily',),
    ('WEEKLY', 'weekly'),
    ('EVERY_TWO_WEEKS', 'every two weeks', {'freq': rrule.WEEKLY, 'interval': 2}),
)
class OccurrenceSeries(SequentialOccurrenceSeriesFactory.construct(calendar=User, rule_choices=RRULES_CHOICES)):
    pass

class Occurrence(SequentialOccurrenceFactory.construct(event=OccurrenceSeries)):
    name = models.CharField(max_length=128, blank=True)

    def __unicode__(self):
        return '%s (%s - %s)' % (self.event, self.start, self.end)

class Models(TestCase):
    def setUp(self):
        self.user_test = User.objects.create_user(
                username='test', password='test', email='test@example.com'
        )
        self.now = datetime.datetime.now().replace(microsecond=0)

    def test_initial_generation_creates_proper_occurrence_number(self):
        now = datetime.datetime.now().replace(microsecond=0)
        end_recurring = now+datetime.timedelta(weeks=4)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        event.get_occurrences(commit=True)

        rule = rrule.rrule(rrule.DAILY)
        self.assertEqual(event.occurrences.count(), len(list(rrule.rrule(dtstart=now, until=end_recurring, freq=rrule.DAILY))))

    def test_extending_recurring_period_generates_additional_occurrences(self):
        now = datetime.datetime.now()
        now = now.replace(microsecond=0)
        end_recurring = now + datetime.timedelta(weeks=4)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        event.get_occurrences(commit=True)

        new_end = end_recurring + datetime.timedelta(weeks=4)
        event.update_recurring_period(new_end)
        self.assertEqual(event.occurrences.count(), len(list(rrule.rrule(dtstart=now, until=new_end, freq=rrule.DAILY))))

    def test_add_event_fails_for_occurrences_time_collision(self):
        now = datetime.datetime.now()
        end_recurring = now + datetime.timedelta(days=3)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        event.get_occurrences(commit=True)

        overlapping_start = now+datetime.timedelta(minutes=30)
        event = OccurrenceSeries(
            start=overlapping_start,
            end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        self.assertRaises(ValidationError, lambda: event.full_clean())

    def test_add_onetime_event_fails_for_occurrences_time_collision(self):
        now = datetime.datetime.now()
        end_recurring = now + datetime.timedelta(weeks=3)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='WEEKLY'
        )
        event.get_occurrences(commit=True)

        overlapping_start = now+datetime.timedelta(minutes=30)
        event = OccurrenceSeries(
            start=overlapping_start,
            end=now+datetime.timedelta(hours=1),
            calendar=self.user_test, rule='ONCE'
        )
        self.assertRaises(ValidationError, lambda: event.full_clean())

    def test_add_event_fails_for_identical_events(self):
        start = datetime.datetime.now()
        end = start + datetime.timedelta(hours=1)
        end_recurring = start + datetime.timedelta(days=3)
        event = OccurrenceSeries.objects.create(start=start, end=end,
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        event.get_occurrences(commit=True)
        event = OccurrenceSeries(
            start=start,
            end=end,
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        self.assertRaises(ValidationError, lambda: event.full_clean())

    def test_occurrence_extending_fails_for_time_collision(self):
        now = datetime.datetime.now()
        end_recurring = now + datetime.timedelta(days=3)
        event = OccurrenceSeries.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=end_recurring,
            calendar=self.user_test, rule='DAILY'
        )
        occurrences = event.get_occurrences(commit=True)
        occurrence_1 = occurrences[0]
        occurrence_2 = occurrences[1]
        occurrence_1.start = occurrence_2.start + (occurrence_2.end - occurrence_2.start)/2
        occurrence_1.end = occurrence_2.end + datetime.timedelta(hours=1)
        self.assertRaises(ValidationError, lambda: occurrence_1.full_clean())

    def test_event_validation_does_not_generates_too_long_sql_query(self):
        #Sqlite raises DatabaseError for query with too many variables.
        #Dynamic query is used in OccurrenceSeries validation method where
        #all occurrences time parameters are inserted into the query.
        event = OccurrenceSeries(start=self.now, end=self.now+datetime.timedelta(hours=1),
            end_recurring_period=self.now+datetime.timedelta(weeks=4),
            calendar=self.user_test, rule='HOURLY'
        )
        event.save()
        event.get_occurrences(commit=True)
