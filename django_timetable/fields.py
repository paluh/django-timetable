from dateutil import rrule

from django.db import models
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _

class RruleField(models.CharField):
    description = _("Time recurrency rule (for example: 'weekly', 'daily').")
    __metaclass__ = models.SubfieldBase

    class RruleWrapper(object):
        def __init__(self, name, **rrule_params):
            self.name = name
            #validate params
            try:
                rrule.rrule(**rrule_params)
            except TypeError:
                raise ValueError("Could ont apply your params to rrule!")
            self.params = rrule_params

        def __call__(self, dtstart, until):
            params = self.params.copy()
            params.update({
                'dtstart': dtstart,
                'until': until,
            })
            return list(rrule.rrule(**params))

        def __eq__(self, other):
            return isinstance(other, self.__class__) and self.params == other.params

    def __init__(self, *args, **kwargs):
        choices = kwargs.get('choices', None)
        if not choices:
            raise AttributeError('You have to pass rrule choices to this field!')
        parsed_choices = []
        self.name2rrule = {}
        for choice in choices:
            if len(choice) == 3:
                self.name2rrule[choice[0]] = RruleField.RruleWrapper(choice[0], **choice[2])
                parsed_choices.append((choice[0], choice[1]))
            elif choice[0] == '':
                parsed_choices.append(choice)
            else:
                self.name2rrule[choice[0]] = RruleField.RruleWrapper(choice[0], freq=getattr(rrule, choice[0]))
                parsed_choices.append(choice)

        kwargs['choices'] = parsed_choices
        super(RruleField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if isinstance(value, basestring):
            return value
        if isinstance(value, RruleField.RruleWrapper):
            return value.name
        return ''

    def get_db_prep_save(self, value, connection=None):
        return self.get_prep_value(value)

    def to_python(self, value):
        if isinstance(value, RruleField.RruleWrapper):
            return value
        return self.name2rrule.get(value, None)

    def validate(self, value, model_instance):
        # coerce value back to a string to validate correctly
        return super(RruleField, self).validate(self.get_prep_value(value), model_instance)

    def run_validators(self, value):
        # coerce value back to a string to validate correctly
        return super(RruleField, self).run_validators(self.get_prep_value(value))

