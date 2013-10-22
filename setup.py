from setuptools import setup, find_packages

DESCRIPTION = "A reusable Django application to represent recurring occurrences/events"

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.textile').read()
except:
    pass

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Framework :: Django',
]

setup(
    name='django-timetable',
    version='2013.10.1',
    packages=find_packages(),
    include_package_data=True,
    author='Paluh',
    author_email='paluho@gmail.com',
    url='https://github.com/paluh/django-timetable',
    license='MIT',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    platforms=['any'],
    classifiers=CLASSIFIERS,
    install_requires=['dateutils']
)

