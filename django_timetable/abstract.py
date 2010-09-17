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
            clsname = ('%s%x' % (cls.__name__, hash(key))) \
                    .replace('-', '_')
            cls._classcache[key] = type(clsname, (cls, ), attrs)
        return cls._classcache[key]
