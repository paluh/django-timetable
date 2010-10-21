from django.db import models

class AbstractMixin(object):
    _cls_counter = 0

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
        cls._cls_counter += 1
        clsname = '%s_%i' % (cls.__name__, cls._cls_counter)
        return type(clsname, (cls, ), attrs)
