# -*- coding:utf-8 -*-
from django.db import models
from django.utils.translation import ugettext as _
from django.db.models import permalink

class AbstractModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(AbstractModelMetaclass, cls).__new__
        if bases == (object, ):
            return super_new(cls, name, bases, attrs)
        new_attrs = attrs.copy()
        module = attrs['__module__']
        new_cls = super_new(cls, name, bases, {'__module__': module})
        fields = getattr(new_cls, '_fields', {}).copy()
        for key, val in attrs.items():
            if key not in ['construct', '__new__']:
                fields[key] = val
        new_attrs['_fields'] = fields
        new_class = super_new(cls, name, bases, new_attrs)
        return new_class

class AbstractModelFactory(object):
    __metaclass__ = AbstractModelMetaclass

    @classmethod
    def construct(cls):
        return {}

    def __new__(cls, *args, **kwargs):
        attrs = cls._fields.copy()
        attrs.update(cls.construct(*args, **kwargs))
        attrs['__module__'] = cls.__module__
        attrs['Meta'] = type('Meta', (), {'abstract': True})
        new_class = type(cls.__name__, (models.Model, ), attrs)
        return new_class

from django.db import models

class AbstractMixin(object):
    _classcache = {}

    @classmethod
    def contribute(cls):
        return {}

    @classmethod
    def construct(cls, *args, **kwargs):
        attrs = cls.contribute(*args, **kwargs)
        attrs.update({
            '__module__': cls.__module__,
            'Meta': type('Meta', (), {'abstract': True}),
        })
        key = (args, tuple(kwargs.items()))
        if not key in cls._classcache:
            clsname = ('%s%x' % (cls.__name__,
                    hash(key))).replace('-', '_')
            cls._classcache[key] = type(clsname, (cls, ), attrs)
        return cls._classcache[key]

