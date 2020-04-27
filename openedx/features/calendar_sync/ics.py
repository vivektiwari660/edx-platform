""" Generate .ics files from a user schedule """

from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.utils.translation import gettext as _
from icalendar import Calendar, Event, vCalAddress, vText

from lms.djangoapps.courseware.courses import get_course_assignments
from openedx.core.djangoapps.site_configuration.helpers import get_value
from openedx.core.djangolib.markup import HTML

from . import get_calendar_event_id


def get_calendar_event_id(user_id, block_key, date_type, hostname):
    """
    Creates a unique event id based on a user and a course block key

    Parameters:
        user_id (int): A user id context for the calendar event
        block_key (str): The block key containing the date for the calendar event
        date_type (str): The type of the date (e.g. 'due', 'start', 'end', etc.)
        hostname (str): A hostname to namespace this id (e.g. 'open.edx.org')
    Returns:
        event id (str)
    """
    return '{}.{}.{}@{}'.format(user_id, block_key, date_type, hostname)


def generate_ics_for_event(uid, title, description, now, start, organizer_name, organizer_email):
    """
    Generates an ics-formatted bytestring for the given event information.

    To pretty-print the bytestring, do: `ics.decode('utf8').replace('\r\n', '\n')`
    """
    # icalendar library: https://icalendar.readthedocs.io/en/latest/
    # ics format spec: https://tools.ietf.org/html/rfc2445
    # ics conventions spec: https://tools.ietf.org/html/rfc5546

    organizer = vCalAddress('mailto:' + organizer_email)
    organizer.params['cn'] = vText(organizer_name)

    event = Event()
    event.add('uid', uid)
    event.add('dtstamp', now)
    event.add('organizer', organizer, encode=0)
    event.add('summary', title)
    event.add('description', description)
    event.add('dtstart', start)
    event.add('duration', timedelta(0))
    event.add('transp', 'TRANSPARENT')  # available, rather than busy

    cal = Calendar()
    cal.add('prodid', '-//Open edX//calendar_sync//EN')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')
    cal.add_component(event)

    return cal.to_ical()


def generate_ics_for_course_assignments(course, user, request):
    """
    Generates ics-formatted bytestrings of all assignments for a given course and user.

    To pretty-print each bytestring, do: `ics.decode('utf8').replace('\r\n', '\n')`

    Returns an iterable of ics files, each one representing an assignment.
    """
    assignments = get_course_assignments(course.id, user, request)
    platform_name = get_value('platform_name', settings.PLATFORM_NAME)
    platform_email = get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
    now = datetime.now(pytz.utc)

    return (
        generate_ics_for_event(
            now=now,
            organizer_name=platform_name,
            organizer_email=platform_email,
            start=assignment.date,
            title=assignment.title,
            description=HTML(_('{assignment} is due for {course}.')).format(
                assignment=assignment.title,
                course=course.display_name_with_default,
            ),
            uid=get_calendar_event_id(user.id, str(assignment.block_key), 'due', request.site.domain),
        )
        for assignment in assignments
    )


def generate_ics_for_course_start(course, request):
    """
    Generates an ics-formatted bytestring of the start date for a course.

    To pretty-print each bytestring, do: `ics.decode('utf8').replace('\r\n', '\n')`
    """
    platform_name = get_value('platform_name', settings.PLATFORM_NAME)
    platform_email = get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
    now = datetime.now(pytz.utc)

    return generate_ics_for_event(
        now=now,
        organizer_name=platform_name,
        organizer_email=platform_email,
        start=course.start_date,
        title=_('{course} Begins').format(course=course.display_name_with_default),
        description='',
        uid=get_calendar_event_id(0, str(course.id), 'start', request.site.domain),
    )
