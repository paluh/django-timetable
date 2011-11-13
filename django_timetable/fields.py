from django.db.models.fields import BLANK_CHOICE_DASH
from django.utils.translation import ugettext
from dateutil import rrule
from functools import partial

from django.db import models

class RruleField(models.PositiveIntegerField):
    """
    Simple RruleField which can represents regular time periods (interval and frequency).
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, frequency, *args, **kwargs):
        self.frequency = frequency
        super(RruleField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None or isinstance(value, partial):
            return value
        value = super(RruleField, self).to_python(value)
        return partial(rrule.rrule, self.frequency,
                       interval=value)

    def validate(self, value, model_instance):
        if isinstance(value, partial):
            value = value.keywords['interval']
        return super(RruleField, self).validate(value, model_instance)

    def get_db_prep_value(self, value):
        if (value is None) or isinstance(value, int):
            return value
        return value.keywords['interval']

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val:
            return val.keywords['interval']
        return ''


class ComplexRruleField(models.CharField):
    """
    ComplexRruleField which can represent more complex situations based on rrule
    definitions.
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        #you can define rrules consts by:
        #  * creating tuple which contains known interval value name from rrule module,
        #       for example: rrule.WEEKLY -> ('WEEKLY', '<display value>')
        #  * creating tuple of three values ('<db_const>', '<display value>', <dict of dateutil.rrule.rrule init parameters>),
        #       for example: ('EVERY_TWO_WEEKS', '<display value>', {'freq': rrule.WEEKLY, 'interval': 2})
        #
        choices = kwargs.pop('choices', None) or (
            ('', ugettext('Once')),
            ('DAILY', ugettext('Daily')),
            ('WEEKLY', ugettext('Weekly')),
            #example of more complicated rule
            ('EVERY_TWO_WEEKS', ugettext('Every two weeks'), {'freq': rrule.WEEKLY, 'interval': 2}),
            ('YEARLY', ugettext('Yearly')),
            ('MONTHLY', ugettext('Monthly')),
        )
        parsed_choices = []
        self.blank_choice = BLANK_CHOICE_DASH
        self.name2rrule = {}
        for choice in choices:
            if len(choice) == 3:
                self.name2rrule[choice[0]] = self._get_rrule(choice[0], **choice[2])
                parsed_choices.append((choice[0], choice[1]))
            elif not choice[0]:
                kwargs['blank'] = True
                self.blank_choice = [(choice[0], choice[1])]
            else:
                self.name2rrule[choice[0]] = self._get_rrule(choice[0], freq=getattr(rrule, choice[0]))
                parsed_choices.append(choice)

        kwargs['choices'] = parsed_choices
        kwargs['default'] = kwargs['default'] if kwargs.get('default', None) is not None else (parsed_choices and parsed_choices[0][0] or None)
        kwargs['max_length'] = max(len(value) for (value, display) in parsed_choices)
        super(ComplexRruleField, self).__init__(*args, **kwargs)

    def get_choices(self, *args, **kwargs):
        kwargs['blank_choice'] = kwargs.get('blank_choice', self.blank_choice)
        return super(ComplexRruleField, self).get_choices(*args, **kwargs)

    def get_flatchoices(self, *args, **kwargs):
        kwargs['blank_choice'] = kwargs.get('blank_choice', self.blank_choice)
        return super(ComplexRruleField, self).get_flatchoices(*args, **kwargs)

    def _get_flatchoices(self):
        """Flattened version of choices tuple."""
        flat = []
        for choice, value in self.choices:
            if isinstance(value, (list, tuple)):
                flat.extend(value)
            else:
                flat.append((self.name2rrule[choice],value))
        return flat
    flatchoices = property(_get_flatchoices)

    def _get_rrule(self, name, **params):
        try:
            #validate params
            rrule.rrule(**params)
        except TypeError:
            raise ValueError("Could ont apply your params to rrule!")
        rule = partial(rrule.rrule, **params)
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
        return super(ComplexRruleField, self).validate(self.get_prep_value(value), model_instance)

    def run_validators(self, value):
        # coerce value back to a string to validate correctly
        return super(ComplexRruleField, self).run_validators(self.get_prep_value(value))

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        rules=[(
            (RruleField, ),
            [],
            {'frequency': ['frequency', {}]})
        ],
        patterns=['django_timetable\.fields\.']
    )
except ImportError:
    pass


