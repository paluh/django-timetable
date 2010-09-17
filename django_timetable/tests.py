import datetime
from dateutil import rrule

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from .models import EventFactory, OccurrenceFactory, RruleChoice

class Event(EventFactory.construct()):
    pass

class Occurrence(OccurrenceFactory.construct(event=Event)):
    name = models.CharField(max_length=128, blank=True)

    def __unicode__(self):
        return '%s (%s - %s)' % (self.name or self.event.name, self.start, self.end)

class ModelsTests(TestCase):
    def test_get_occurrences_returns_proper_new_objects_number(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = Event.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end)
        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        self.assertEqual(len(occurrences), len(rule.between(now, end, inc=True)))

    def test_get_occurrences_returns_one_object_for_onetime_rule(self):
        now = datetime.datetime.now()
        event = Event.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='ONCE')
        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end, commit=True)
        self.assertEqual(event.occurrences.count(), 1)

    def test_get_occurrences_saves_objects_on_demand(self):
        now = datetime.datetime.now()
        event = Event.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')

        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end)

        self.assertEqual(event.occurrences.count(), 0)
        occurrences = event.get_occurrences(now, end, commit=True)
        self.assertEqual(event.occurrences.count(), len(occurrences))

    def test_get_occurrences_returns_proper_number_when_some_tracks_already_exists(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = Event.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')

        rule = rrule.rrule(rrule.HOURLY, dtstart=now)
        end = now+datetime.timedelta(hours=8)
        event.get_occurrences(now, end, commit=True)

        end = now+datetime.timedelta(days=1)
        occurrences = event.get_occurrences(now, end)
        self.assertEqual(len(occurrences),
                len(rule.between(now, end, inc=True)))

    def test_get_occurrences_returns_proper_number_for_custom_rrule(self):
        now = datetime.datetime.now().replace(microsecond=0)
        event = Event.objects.create(start=now, end=now+datetime.timedelta(hours=1),
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='EVERY_TWO_WEEKS')

        rule = rrule.rrule(dtstart=now, **RruleChoice.get_params('EVERY_TWO_WEEKS'))
        end = now+datetime.timedelta(weeks=4)
        event.get_occurrences(now, end)

        occurrences = event.get_occurrences(now, end)
        self.assertEqual(len(occurrences),
                len(rule.between(now, end, inc=True)))

    def test_save_fails_when_start_is_greater_then_end(self):
        now = datetime.datetime.now()
        event = Event(start=now+datetime.timedelta(hours=1), end=now,
            end_recurring_period=now+datetime.timedelta(weeks=54), rule='HOURLY')
        self.assertRaises(ValidationError, lambda: event.full_clean())
