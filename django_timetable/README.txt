django_timetable
================

This is lightweight django app for creating recurring events calendar (one time event too ;-). It's inspired by django-schedule - main difference is use of abstract model factory so it's easier to extend and use this app. Additionally there is sequential_calendar app which you can use to restrict occurrences overlapping.

Thanks to Patrys (Patryk Zawadzki) implementation of abstract models factory (look into abstraction.py and here: http://room-303.com/blog/2010/04/27/django-abstrakcji-ciag-dalszy/ - it's in polish but code examples are self-expanatory) you can subclass event and occurrences models as you want without using generic relations.

USAGE
To create real model from provided factories you have to call construct.

1. timetable

from timetable.models import EventFactory, OccurrenceFactory

class Programme(SequentialEventFactory.construct(calendar=Radio)):
    title = models.CharField(max_length=128)

class ProgrammeOccurrence(SequentialEventFactory.construct(event=Event)):
    summary = models.TextField()


2. timetable.sequential_calendar

This app adds calendar reference to events and implements additional constraint to event
occurrences: they don't overllap in one calendar.

Let assume that we are going to implement radio schedule:

from timetable.sequential_calendar.models import (
    SequentialEventFactory, SequentialOccurrenceFactory)

class Radio(models.Model):
    name = models.CharField(max_length=128)

class Programme(SequentialEventFactory.construct(calendar=Radio)):
    title = models.CharField(max_length=128)

class ProgrammeOccurrence(SequentialEventFactory.construct(event=Event)):
    summary = models.TextField()

Sequential event is gready, so during creation it generates all occurrences
(so be carefull restrict end_recurring_period to some sane value).

>>> import datetime
>>> from radio.models import Radio, Programme
>>> radio = Radio.objects.create(name="CCB radio one")
>>> start = datetime(2010, 1, 1, 13, 0)
>>> programme = Programme.objects.create(
        title='And Now for Something Completely Different',
        calendar=radio,
        rule='WEEKLY',
        start=start,
        end=start+datetime.timedelta(hours=1),
        end_recurring_period=start+datetime.timedelta(weeks=5)
)

TESTING
To test this apps just run: ./manage.py django_timetable sequential_calendar after installing this app in your project.
