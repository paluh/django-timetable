from dateutil import rrule
from functools import partial

from django.conf import settings
from django.db import models
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

MAX_RRULE_LENGTH = getattr(settings, "MAX_RRULE_LENGTH", 128)

class RruleField(models.CharField):
    """
        RruleField is callable - it's curried rrule.rrule function which expects dtstart and until kwargs.
        Look into django_timetable.models for example.
    """

    description = _("Time recurrency rule (for example: 'weekly', 'daily').")
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        #you can define rrules consts by:
        #  * creating tuple which contains known interval value name from rrule module,
        #       for example: rrule.WEEKLY -> ('WEEKLY', '<display value>')
        #  * creating tuple of three values ('<db_const>', '<display value>', <dict of dateutil.rrule.rrule init parameters>),
        #       for example: ('EVERY_TWO_WEEKS', '<display value>', {'freq': rrule.WEEKLY, 'interval': 2})
        #
        #Note: there is only one etmpy rule allowed and it value should be: ''
        choices = kwargs.pop('choices', None) or (
            ('', _('Once')),
            ('DAILY', _('Daily')),
            ('WEEKLY', _('Weekly')),
            #example of more complicated rule
            ('EVERY_TWO_WEEKS', _('Every two weeks'), {'freq': rrule.WEEKLY, 'interval': 2}),
            ('YEARLY', _('Yearly')),
            ('MONTHLY', _('Monthly')),
        )
        parsed_choices = []
        self.name2rrule = {}
        for choice in choices:
            if len(choice) == 3:
                self.name2rrule[choice[0]] = self._get_rrule(choice[0], **choice[2])
                parsed_choices.append((choice[0], choice[1]))
            elif choice[0] == '':
                parsed_choices.append(choice)
            else:
                self.name2rrule[choice[0]] = self._get_rrule(choice[0], freq=getattr(rrule, choice[0]))
                parsed_choices.append(choice)

        kwargs['choices'] = parsed_choices
        kwargs['default'] = kwargs['default'] if kwargs.get('default', None) is not None else parsed_choices[0]
        kwargs['max_length'] = max([MAX_RRULE_LENGTH] + [len(x[0]) for x in parsed_choices])
        super(RruleField, self).__init__(*args, **kwargs)

    def _get_rrule(self, name, **params):
        try:
            #validate params
            rrule.rrule(**params)
        except TypeError:
            raise ValueError("Could ont apply your params to rrule!")
        rule = lambda **kwargs: list(partial(rrule.rrule, **params)(**kwargs))
        rule.name = name
        return rule

    def get_prep_value(self, value):
        if isinstance(value, basestring):
            return value
        if value is None:
            return ''
        return value.name

    def get_db_prep_save(self, value, connection=None):
        return self.get_prep_value(value)

    def to_python(self, value):
        if isinstance(value, basestring):
            return self.name2rrule.get(value, None)
        return value

    def validate(self, value, model_instance):
        # coerce value back to a string to validate correctly
        return super(RruleField, self).validate(self.get_prep_value(value), model_instance)

    def run_validators(self, value):
        # coerce value back to a string to validate correctly
        return super(RruleField, self).run_validators(self.get_prep_value(value))

try:
    from south.modelsinspector import add_introspection_rules

    #be careful when migrating models with rrule - if your choices value is not in
    #default set (look into RruleField.__init__) occurrence.rule will be None!
    add_introspection_rules(
        rules=[((RruleField, ), [], {"max_length": ["max_length", { "default": MAX_RRULE_LENGTH }]})],
        patterns=['django_timetable\.fields\.']
    )
except ImportError:
    pass
