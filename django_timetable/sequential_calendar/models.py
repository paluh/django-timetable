import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from ..models import OccurrenceSeriesFactory, OccurrenceFactory

class TimeColisionError(ValidationError):
    pass

class CalendarOccurrenceSeriesFactory(OccurrenceSeriesFactory):
    class Meta:
        abstract = True

    @classmethod
    def contribute(cls, **kwargs):
        calendar = kwargs.pop('calendar', None)
        fields = super(CalendarOccurrenceSeriesFactory, cls).contribute(**kwargs)

        if not calendar:
            raise ValueError("Sequential events requires calendar model.")
        fields['calendar'] = models.ForeignKey(calendar, related_name="events")
        return fields

class SequentialOccurrenceSeriesFactory(CalendarOccurrenceSeriesFactory):
    class Meta:
        abstract = True

    def update_recurring_period(self, new_end, defaults=None):
        self.end_recurring_period = new_end
        self.save()
        now = datetime.datetime.now()
        self.clean()
        self.get_occurrences(now, self.end_recurring_period, commit=True, defaults=defaults)
        self.occurrences.filter(start__gt=self.end_recurring_period).delete()

    def clean(self):
        super(SequentialOccurrenceSeriesFactory, self).clean()
        end_recurring_period = self.end_recurring_period
        if not end_recurring_period:
            end_recurring_period = self.end
        if not self.end or not self.start:
            return

        MAX_SQL_VARS = getattr(settings, 'MAX_SQL_VARS', 500)
        occurrences = self.get_occurrences(self.start, end_recurring_period)
        query = Q()
        for index, occurrence in enumerate(occurrences):
            #FIXME: this event model assumes that event is period: start <= event < end
            #probably this should be customizable
            subquery = (Q(occurrences__start__gte=occurrence.start) & Q(occurrences__start__lt=occurrence.end)) \
                    | (Q(occurrences__start__lte=occurrence.start) & Q(occurrences__end__gt=occurrence.start))
            if occurrence.pk:
                subquery &= ~Q(occurrences__pk=occurrence.pk)
            query |= subquery
            #this prevents 'too many SQL variables' raised by sqlite
            if index and index%(MAX_SQL_VARS/5)== 0:
                if self.calendar.events.filter(query).exists():
                    raise TimeColisionError(
                        message=_("Event occurrence has time collision with other occurrence from this calendar."),
                        params=self.calendar.events.filter(query).order_by('start')[0],
                    )
                query = Q()
        if self.calendar.events.filter(query).exists():
            raise TimeColisionError(
                message=_("Event occurrence has time collision with other occurrence from this calendar."),
                params=self.calendar.events.filter(query).order_by('start')[0],
            )

class SequentialOccurrenceFactory(OccurrenceFactory):
    class Meta:
        abstract = True

    def clean(self):
        super(SequentialOccurrenceFactory, self).clean()
        if self.id:
            query = (Q(event__calendar=self.event.calendar) & ~Q(pk=self.pk))\
                    & ( (Q(start__gte=self.start) & Q(start__lt=self.end))
                        | (Q(start__lte=self.start) & Q(end__gt=self.start))
                    )
            if self.__class__.objects.filter(query).exists():
                raise TimeColisionError(_("Occurrence has time collision with other occurrence from this calendar."))
