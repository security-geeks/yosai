import pytest
from unittest import mock
import datetime
import pytz
import collections
from ..doubles import (
    MockSession,
)

from yosai.core import (
    CachingSessionStore,
    DelegatingSession,
    DefaultEventBus,
    Event,
    ExecutorServiceSessionValidationScheduler,
    ExpiredSessionException,
    IllegalArgumentException,
    MemorySessionStore,
    SessionEventException,
    SessionHandler,
    StoppableScheduledExecutor,
    StoppedSessionException,
    IllegalStateException,
    InvalidSessionException,
    UnknownSessionException,
)

# ----------------------------------------------------------------------------
# SessionEventHandler
# ----------------------------------------------------------------------------


def test_seh_notify_start_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_start

    """
    seh = session_event_handler
    mockevent = Event(source='SessionEventHandler',
                      event_topic='SESSION.START',
                      results=mock_session.session_id)

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_start(mock_session)
        event_publish.assert_called_with(mockevent.event_topic, event=mockevent)


def test_seh_notify_start_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(mock_session, '_session_id')

    with pytest.raises(SessionEventException):
        seh.notify_start(mock_session)


def test_seh_notify_stop_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_stop
    """
    seh = session_event_handler
    mockevent = Event(source='SessionEventHandler',
                      event_topic='SESSION.STOP',
                      results='sessiontuple')

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_stop('sessiontuple')
        event_publish.assert_called_with(mockevent.event_topic, event=mockevent)


def test_seh_notify_stop_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(seh, '_event_bus')

    with pytest.raises(SessionEventException):
        seh.notify_stop(mock_session)


def test_seh_notify_expiration_publishes(session_event_handler, mock_session):
    """
    unit tested:  notify_expiration
    """
    seh = session_event_handler
    mockevent = Event(source='SessionEventHandler',
                      event_topic='SESSION.EXPIRE',
                      results='sessiontuple')

    with mock.patch.object(seh.event_bus, 'publish') as event_publish:
        event_publish.return_value = None
        seh.notify_expiration('sessiontuple')
        event_publish.assert_called_with(mockevent.event_topic, event=mockevent)


def test_seh_notify_expiration_raises(session_event_handler, mock_session, monkeypatch):
    seh = session_event_handler
    monkeypatch.delattr(seh, '_event_bus')

    with pytest.raises(SessionEventException):
        seh.notify_expiration(mock_session)


# ----------------------------------------------------------------------------
# SessionHandler
# ----------------------------------------------------------------------------

def test_sh_set_sessionstore(session_handler):
    """
    unit tested:  session_store.setter

    test case:
    the session_store property sets the attribute and calls a method
    """
    sh = session_handler
    with mock.patch.object(SessionHandler,
                           'apply_cache_handler_to_session_store') as achss:
        achss.return_value = None

        sh.session_store = 'sessionstore'

        achss.assert_called_once_with()


def test_sh_set_cache_handler(session_handler):
    """
    unit tested:  cache_handler.setter

    test case:
    the cache_handler property sets the attribute and calls a method
    """
    sh = session_handler

    with mock.patch.object(SessionHandler,
                           'apply_cache_handler_to_session_store') as achss:
        achss.return_value = None

        sh.cache_handler = 'cache_handler'

        achss.assert_called_once_with()


def test_sh_achtsd(
        session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  apply_cache_handler_to_session_store

    test case:
    when a sessionStore is configured, the sessionStore sets the cachehandler
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_cache_handler', 'cachehandler')
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    sh.apply_cache_handler_to_session_store()
    assert sh.session_store.cache_handler == 'cachehandler'


def test_sh_achtsd_raises(
        session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  apply_cache_handler_to_session_store

    test case:
    if no sessionStore configured, will return gracefully
    """
    sh = session_handler
    monkeypatch.setattr(sh, '_cache_handler', 'cachehandler')
    monkeypatch.delattr(caching_session_store, '_cache_handler')
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    sh.apply_cache_handler_to_session_store()


def test_sh_create_session(
        session_handler, monkeypatch, caching_session_store):
    sh = session_handler
    monkeypatch.setattr(caching_session_store, 'create', lambda x: x)
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    result = sh.create_session('session')
    assert result == 'session'


def test_sh_delete(
        session_handler, monkeypatch, caching_session_store):
    sh = session_handler
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    with mock.patch.object(CachingSessionStore, 'delete') as css_del:
        css_del.return_value = None
        sh.delete('session')
        css_del.assert_called_once_with('session')


def test_sh_retrieve_session_w_sessionid_raising(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    when no session can be retrieved from a data source when using a sessionid,
    an exception is raised
    """
    sh = session_handler
    css = caching_session_store

    monkeypatch.setattr(css, 'read', lambda x: None)
    monkeypatch.setattr(sh, '_session_store', css)

    with pytest.raises(UnknownSessionException):
        sh._retrieve_session(session_key)


def test_sh_retrieve_session_withsessionid_returning(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    retrieves session from a data source, using a sessionid as parameter,
    and returns it
    """
    sh = session_handler
    css = caching_session_store

    monkeypatch.setattr(css, 'read', lambda x: x)
    monkeypatch.setattr(sh, '_session_store', css)

    result = sh._retrieve_session(session_key)
    assert result == 'sessionid123'


def test_sh_retrieve_session_withoutsessionid(
        session_handler, monkeypatch, caching_session_store, session_key):
    """
    unit tested:  retrieve_session

    test case:
    fails to obtain a session_id value from the sessionkey, returning None
    """
    sh = session_handler

    monkeypatch.setattr(session_key, 'session_id', None)

    result = sh._retrieve_session(session_key)
    assert result is None


def test_sh_dogetsession_none(session_handler, monkeypatch, session_key):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session fails to returns a session, returning None
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: None)

    result = sh.do_get_session(session_key)
    assert result is None


def test_sh_dogetsession_notouch(session_handler, monkeypatch, session_key):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session returns a session
    - validate will be called
    - auto_touch is False by default, so skipping its clode block
    - session is returned
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: 'session')

    with mock.patch.object(SessionHandler, 'validate') as sh_validate:
        sh_validate.return_value = None

        result = sh.do_get_session(session_key)
        sh_validate.assert_called_once_with('session', session_key)
        assert result == 'session'


def test_sh_dogetsession_touch(
        session_handler, monkeypatch, session_key, mock_session):
    """
    unit tested: do_get_session

    test case:
    - retrieve_session returns a session
    - validate will be called
    - auto_touch is set True, so its clode block is called
    - session is returned
    """
    sh = session_handler

    monkeypatch.setattr(sh, '_retrieve_session', lambda x: mock_session)
    monkeypatch.setattr(sh, 'auto_touch', True)

    with mock.patch.object(SessionHandler, 'validate') as sh_validate:
        sh_validate.return_value = None
        with mock.patch.object(SessionHandler, 'on_change') as oc:
            oc.return_value = None
            with mock.patch.object(mock_session, 'touch') as ms_touch:
                ms_touch.return_value = None

                result = sh.do_get_session(session_key)

                sh_validate.assert_called_once_with(mock_session, session_key)
                ms_touch.assert_called_once_with()
                oc.assert_called_once_with(mock_session)

                assert result == mock_session


def test_sh_validate_succeeds(session_handler, mock_session, monkeypatch,
                              session_key):
    """
    unit test:  validate

    test case:
    basic code path exercise
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as sessval:
        sessval.return_value = None
        sh.validate(mock_session, 'sessionkey123')


def test_sh_validate_expired(session_handler, mock_session, monkeypatch,
                             session_key):
    """
    unit test:  validate

    test case:
    do_validate raises expired session exception, calling on_expiration and
    raising
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as ms_dv:
        ms_dv.side_effect = ExpiredSessionException
        with mock.patch.object(SessionHandler, 'on_expiration') as sh_oe:
            sh_oe.return_value = None
            with pytest.raises(ExpiredSessionException):

                sh.validate(mock_session, 'sessionkey123')

                sh_oe.assert_called_once_with(mock_session,
                                              ExpiredSessionException,
                                              'sessionkey123')

def test_sh_validate_invalid(session_handler, mock_session, monkeypatch,
                             session_key):
    """
    unit test:  validate

    test case:
    do_validate raises expired session exception, calling on_expiration and
    raising
    """
    sh = session_handler

    with mock.patch.object(mock_session, 'validate') as ms_dv:
        ms_dv.side_effect = StoppedSessionException
        with mock.patch.object(SessionHandler, 'on_invalidation') as sh_oe:
            sh_oe.return_value = None
            with pytest.raises(InvalidSessionException):

                sh.validate(mock_session, 'sessionkey123')

                sh_oe.assert_called_once_with(mock_session,
                                              ExpiredSessionException,
                                              'sessionkey123')


def test_sh_on_stop(session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_stop

    test case:
    updated last_access_time and calls on_change
    """
    sh = session_handler
    monkeypatch.setattr(mock_session, '_last_access_time', 'anything')
    monkeypatch.setattr(mock_session, '_stop_timestamp', None, raising=False)
    monkeypatch.setattr(mock_session, '_stop_timestamp',
                        datetime.datetime.now(pytz.utc))
    with mock.patch.object(sh, 'on_change') as mock_onchange:
        sh.on_stop(mock_session)
        mock_onchange.assert_called_with(mock_session)
        assert mock_session.last_access_time == mock_session.stop_timestamp


def test_sh_after_stopped(session_handler, monkeypatch):
    """
    unit tested:  after_stopped

    test case:
    if delete_invalid_sessions is True, call delete method
    """
    sh = session_handler
    monkeypatch.setattr(sh, 'delete_invalid_sessions', True)
    with mock.patch.object(sh, 'delete') as sh_delete:
        sh_delete.return_value = None
        sh.after_stopped('session')
        sh_delete.assert_called_once_with('session')


def test_sh_on_expiration(session_handler, monkeypatch, mock_session):
    """
    unit tested:  on_expiration

    test case:
    set's a session to expired and then calls on_change
    """
    sh = session_handler
    with mock.patch.object(sh, 'on_change') as sh_oc:
        sh_oc.return_value = None
        sh.on_expiration(mock_session)
        sh_oc.assert_called_once_with(mock_session)


@pytest.mark.parametrize('ese,session_key',
                         [('ExpiredSessionException', None),
                          (None, 'sessionkey123')])
def test_sh_on_expiration_onenotset(session_handler, ese, session_key):
    """
    unit tested:  on_expiration

    test case:
        expired_session_exception or session_key are set, but not both
    """
    sh = session_handler

    with pytest.raises(IllegalArgumentException):
        sh.on_expiration(session='testsession',
                         expired_session_exception=ese,
                         session_key=session_key)


def test_sh_on_expiration_allset(session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_expiration

    test case:
        all parameters are passed, calling on_change, notify_expiration, and
        after_expired
    """
    sh = session_handler

    session_tuple = collections.namedtuple(
        'session_tuple', ['identifiers', 'session_key'])
    mysession = session_tuple('identifiers', 'sessionkey123')

    monkeypatch.setattr(mock_session, 'get_internal_attribute',
                        lambda x: 'identifiers')
    with mock.patch.object(sh.session_event_handler, 'notify_expiration') as sh_ne:
        sh_ne.return_value = None
        with mock.patch.object(sh, 'after_expired') as sh_ae:
            sh_ae.return_value = None
            with mock.patch.object(sh, 'on_change') as sh_oc:
                sh_oc.return_value = None

                sh.on_expiration(session=mock_session,
                                 expired_session_exception='ExpiredSessionException',
                                 session_key='sessionkey123')

                sh_ne.assert_called_once_with(mysession)
                sh_ae.assert_called_once_with(mock_session)
                sh_oc.assert_called_once_with(mock_session)


def test_sh_after_expired(session_handler, monkeypatch):
    """
    unit tested:  after_expired

    test case:
    when delete_invalid_sessions is True, invoke delete method
    """
    sh = session_handler
    monkeypatch.setattr(sh, 'delete_invalid_sessions', True)
    with mock.patch.object(sh, 'delete') as sh_del:
        sh_del.return_value = None

        sh.after_expired('session')

        sh_del.assert_called_once_with('session')


def test_sh_on_invalidation_esetype(session_handler, mock_session):
    """
    unit tested:  on_invalidation

    test case:
        when an exception of type ExpiredSessionException is passed,
        on_expiration is called and then method returns
    """
    sh = session_handler
    ise = ExpiredSessionException('testing')
    session_key = 'sessionkey123'
    with mock.patch.object(sh, 'on_expiration') as mock_oe:
        sh.on_invalidation(session=mock_session, ise=ise, session_key=session_key)
        mock_oe.assert_called_with


def test_sh_on_invalidation_isetype(
        session_handler, mock_session, monkeypatch):
    """
    unit tested:  on_invalidation

    test case:
        when an exception NOT of type ExpiredSessionException is passed,
        an InvalidSessionException higher up the hierarchy is assumed
        and on_stop, notify_stop, and after_stopped are called
    """
    sh = session_handler
    ise = StoppedSessionException('testing')
    session_key = 'sessionkey123'

    session_tuple = collections.namedtuple(
        'session_tuple', ['identifiers', 'session_key'])
    mysession = session_tuple('identifiers', 'sessionkey123')

    monkeypatch.setattr(mock_session, 'get_internal_attribute',
                        lambda x: 'identifiers')

    with mock.patch.object(sh, 'on_stop') as mock_onstop:
        mock_onstop.return_value = None

        with mock.patch.object(sh.session_event_handler,
                               'notify_stop') as mock_ns:
            mock_ns.return_value = None

            with mock.patch.object(sh, 'after_stopped') as mock_as:
                mock_as.return_value = None

                sh.on_invalidation(session=mock_session,
                                   ise=ise,
                                   session_key=session_key)

                mock_onstop.assert_called_once_with(mock_session)
                mock_ns.assert_called_once_with(mysession)
                mock_as.assert_called_once_with(mock_session)


def test_sh_on_change(session_handler, monkeypatch, caching_session_store):
    """
    unit tested:  on_change

    test case:
    passthrough call to session_store.update
    """
    sh = session_handler
    monkeypatch.setattr(sh, '_session_store', caching_session_store)
    with mock.patch.object(sh._session_store, 'update') as ss_up:
        ss_up.return_value = None

        sh.on_change('session')

        ss_up.assert_called_once_with('session')


# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------

def test_avsm_create_session(
        abstract_validating_session_manager, monkeypatch):
    avsm = abstract_validating_session_manager
    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'enable_session_validation_if_necessary') as avsm_esvin:
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'do_create_session') as avsm_dcs:
            avsm_dcs.return_value = 'session'
            result = avsm.create_session('sessioncontext')
            assert avsm_esvin.called and result == 'session'

def test_dsm_do_create_session(
        mock_default_session_manager, monkeypatch, mock_session):
    """
    unit tested:  do_create_session

    test case:
    basic code path exercise-- gets a session instance and calls create w/ it
    """
    mdsm = mock_default_session_manager
    monkeypatch.setattr(mdsm, 'new_session_instance', lambda x: mock_session)
    with mock.patch.object(MockDefaultNativeSessionManager, 'create') as mdsm_create:
        mdsm_create.return_value = None
        result = mdsm.do_create_session('dumbsessioncontext')
        assert result == mock_session

def test_ansm_publish_event_succeeds(abstract_native_session_manager):
    """
    unit tested:  publish_event

    test case:  successful publish of event to event bus
    """
    ansm = abstract_native_session_manager
    with mock.patch.object(DefaultEventBus, 'publish') as meb_pub:
        meb_pub.return_value = None
        ansm.publish_event('dumbevent')
        meb_pub.assert_called_once_with('dumbevent')

def test_ansm_publish_event_fails(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  publish_event

    test case:
    when no event_bus is set, raises an exception
    """
    ansm = abstract_native_session_manager
    monkeypatch.delattr(ansm, '_event_bus')
    with pytest.raises(SessionEventException):
        ansm.publish_event('dumbevent')

def test_ansm_start(abstract_native_session_manager, monkeypatch):
    """
    unit tested:  start

    test case:
    start calls other methods and doesn't compute anything on its own so
    not much to test here other than to exercise the code path
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    monkeypatch.setattr(ansm, 'create_session', lambda x: dumbsession)
    monkeypatch.setattr(ansm, 'apply_session_timeouts', lambda x: None)
    monkeypatch.setattr(ansm, 'on_start', lambda x, y: None)
    monkeypatch.setattr(ansm, 'notify_start', lambda x: None)
    monkeypatch.setattr(ansm, 'create_exposed_session', lambda x, y: dumbsession)

    result = ansm.start('session_context')
    assert result == dumbsession

def test_ansm_apply_session_timeouts(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  apply_session_timeouts

    test case:
    confirms that the timeout attributes are set in the session object and
    that on_change is called
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        ansm.apply_session_timeouts(dumbsession)
        assert (mocky.called and
                dumbsession.absolute_timeout and
                dumbsession.idle_timeout)

def test_ansm_get_session_locates(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested: get_session

    test case:
    lookup_session returns a session, and so create_exposed_session is called
    with it
    """
    ansm = abstract_native_session_manager
    monkeypatch.setattr(ansm, 'lookup_session', lambda x: 'session')
    monkeypatch.setattr(ansm, 'create_exposed_session', lambda x, y: 'ces')

    results = ansm.get_session('key')

    assert results == 'ces'  # asserts that it was called

def test_ansm_get_session_doesnt_locate(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  get_session

    test case:
    lookup session fails to locate a session and so None is returned
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: None)
    results = ansm.get_session('key')

    assert results is None

def test_ansm_lookup_session(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_session

    test case:
    a basic code path exercise confirming that do_get_session is called
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'do_get_session', lambda x: 'dgs_called')
    results = ansm.lookup_session('key')

    assert results == 'dgs_called'

def test_ansm_lookup_required_session_locates(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session finds and returns a session
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: 'session')
    results = ansm.lookup_required_session('key')
    assert results == 'session'  # asserts that it was called

def test_ansm_lookup_required_session_failstolocate(
        abstract_native_session_manager, monkeypatch):
    """
    unit tested:  lookup_required_session

    test case:
    lookup_session fails to locate a session, raising an exception instead
    """
    ansm = abstract_native_session_manager

    monkeypatch.setattr(ansm, 'lookup_session', lambda x: None)
    with pytest.raises(UnknownSessionException):
        ansm.lookup_required_session('key')

def test_ansm_create_exposed_session(abstract_native_session_manager):
    """
    unit tested:  create_exposed_session

    test case:
    basic codepath exercise
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    result = ansm.create_exposed_session(dumbsession)
    assert isinstance(result, DelegatingSession)

def test_ansm_before_invalid_notification(abstract_native_session_manager):
    """
    unit tested:  before_invalid_notification

    test case:
    basic codepath exercise
    """
    ansm = abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234'})()
    result = ansm.before_invalid_notification(dumbsession)
    assert isinstance(result, ImmutableProxiedSession)

def test_ansm_get_start_timestamp(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_start_timestamp

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_start_timestamp('sessionkey')
    expected = datetime.datetime(2015, 6, 17, 19, 43, 51, 818810)
    assert results == expected

def test_ansm_get_last_access_time(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_last_access_time

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_last_access_time('sessionkey')
    expected = datetime.datetime(2015, 6, 17, 19, 45, 51, 818810)
    assert results == expected

def test_ansm_get_absolute_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested:  get_absolute_timeout

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_absolute_timeout('sessionkey')
    expected = datetime.timedelta(minutes=60)
    assert results == expected

def test_ansm_get_idle_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: get_idle_timeout

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    results = ansm.get_idle_timeout('sessionkey')
    expected = datetime.timedelta(minutes=15)
    assert results == expected

def test_ansm_set_idle_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_idle_timeout

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    timeout = datetime.timedelta(minutes=30)
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        ansm.set_idle_timeout('sessionkey123', timeout)
        assert (mocky.called and mock_session.idle_timeout == timeout)

def test_ansm_set_absolute_timeout(
        patched_abstract_native_session_manager, monkeypatch, mock_session):
    """
    unit tested: set_absolute_timeout

    test case:
    basic code exercise, passes through and returns
    """
    ansm = patched_abstract_native_session_manager
    timeout = datetime.timedelta(minutes=30)

    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        ansm.set_absolute_timeout('sessionkey123', timeout)
        assert (mocky.called and mock_session.absolute_timeout == timeout)

def test_ansm_touch(patched_abstract_native_session_manager, mock_session):
    """
    unit tested:  touch

    test case:
    basic code exercise, passes through
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        with mock.patch.object(MockSession, 'touch') as touchy:
            ansm.touch('sessionkey123')
            assert (mocky.called and touchy.called)

def test_ansm_get_host(patched_abstract_native_session_manager):
    """
    unit tested:  get_host

    test case:
    basic code exercise, passes through and returns host
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        result = ansm.get_host('sessionkey123')
        assert result == '127.0.0.1'

def test_ansm_get_attribute_keys_results(
        patched_abstract_native_session_manager):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns a tuple contains 3 mock items
    """
    ansm = patched_abstract_native_session_manager
    result = ansm.get_attribute_keys('sessionkey123')
    assert 'attr2' in result  # arbitrary check

def test_ansm_get_attribute_keys_empty(
        patched_abstract_native_session_manager, monkeypatch):
    """
    unit tested:  get_attribute_keys

    test case:
    basic code exercise, passes through and returns an empty tuple
    """
    ansm = patched_abstract_native_session_manager
    dumbsession = type('DumbSession', (object,), {'session_id': '1234',
                                                  'attribute_keys': None})()
    monkeypatch.setattr(ansm, 'lookup_required_session', lambda x: dumbsession)
    result = ansm.get_attribute_keys('sessionkey123')
    assert result == tuple()

def test_ansm_get_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  get_attribute

    test case:
    basic code exercise, passes through and returns an attribute
    """
    ansm = patched_abstract_native_session_manager
    result = ansm.get_attribute('sessionkey123', 'attr2')
    assert result == 2

def test_ansm_set_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  set_attribute

    test case:
    sets an attribute
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        ansm.set_attribute('sessionkey123', attribute_key='attr321', value=321)
        mocksession = ansm.lookup_required_session('bla')
        assert (mocky.called and
                'attr321' in mocksession.session)

def test_ansm_set_attribute_removes(
        patched_abstract_native_session_manager):
    """
    unit tested:  set_attribute

    test case:
    calling set_attribute without a value results in the removal of an attribute
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(ansm, 'remove_attribute') as mock_ra:
        ansm.set_attribute('sessionkey123', attribute_key='attr1')
        assert mock_ra.called

def test_ansm_remove_attribute(patched_abstract_native_session_manager):
    """
    unit tested:  remove_attribute

    test case:
    successfully removes an attribute
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        result = ansm.remove_attribute('sessionkey123', 'attr3')
        assert result == 3 and mocky.called

def test_ansm_remove_attribute_nothing(patched_abstract_native_session_manager):
    """
    unit tested:  remove_attribute

    test case:
    removing an attribute that doesn't exist returns None
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(MockAbstractNativeSessionManager, 'on_change') as mocky:
        result = ansm.remove_attribute('sessionkey123', 'attr5')
        assert result is None and not mocky.called

def test_ansm_is_valid(patched_abstract_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    a valid sesion returns True
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(MockAbstractNativeSessionManager, 'check_valid') as mocky:
        mocky.return_value = True
        result = ansm.is_valid('sessionkey123')
        assert result

def test_ansm_is_valid_raisefalse(patched_abstract_native_session_manager):
    """
    unit tested:  is_valid

    test case:
    an invalid sesion returns False
    """
    ansm = patched_abstract_native_session_manager

    with mock.patch.object(MockAbstractNativeSessionManager, 'check_valid') as mocky:
        mocky.side_effect = InvalidSessionException
        result = ansm.is_valid('sessionkey123')
        assert result is False

def test_ansm_stop(patched_abstract_native_session_manager):
    """
    unit tested:  stop

    test case:
    basic method exercise, calling methods and completing
    """
    ansm = patched_abstract_native_session_manager
    mocksession = ansm.lookup_required_session('bla')
    with mock.patch.object(MockSession, 'stop') as stop:
        with mock.patch.object(ansm, 'on_stop') as on_stop:
            with mock.patch.object(ansm, 'notify_stop') as notify_stop:
                with mock.patch.object(ansm, 'after_stopped') as after_stopped:
                    ansm.stop('sessionkey123')
                    stop.assert_called_with()
                    on_stop.assert_called_with(mocksession, 'sessionkey123')
                    notify_stop.assert_called_with(mocksession)
                    after_stopped.assert_called_with(mocksession)

def test_ansm_stop_raises(patched_abstract_native_session_manager):
    """
    unit tested:  stop

    test case:
    exception is raised and finally section is executed
    """
    ansm = patched_abstract_native_session_manager
    mocksession = ansm.lookup_required_session('bla')
    with mock.patch.object(MockSession, 'stop') as stop:
        stop.side_effect = InvalidSessionException
        with mock.patch.object(ansm, 'after_stopped') as after_stopped:
            with pytest.raises(InvalidSessionException) as exc:
                ansm.stop('sessionkey123')
            after_stopped.assert_called_with(mocksession)
            assert exc

def test_ansm_check_valid_raises(patched_abstract_native_session_manager):
    """
    unit tested:  check_valid

    test case:
    calls lookup_required_session
    """
    ansm = patched_abstract_native_session_manager
    with mock.patch.object(ansm, 'lookup_required_session') as mocky:
        ansm.check_valid('sessionkey123')
        mocky.assert_called_with('sessionkey123')


# ----------------------------------------------------------------------------
# ExecutorServiceSessionValidationScheduler
# ----------------------------------------------------------------------------

def test_esvs_enable_session_validation(executor_session_validation_scheduler):
    """
    unit tested:  enable_session_validation

    test case:
    interval is set, so service.start() will be invoked and enabled = True
    """

    esvs = executor_session_validation_scheduler
    sse = StoppableScheduledExecutor  # from yosai.concurrency
    with mock.patch.object(sse, 'start') as sse_start:
        esvs.enable_session_validation()
        sse_start.assert_called_with() and esvs.is_enabled


def test_esvs_run(executor_session_validation_scheduler):
    """
    unit tested:  run

    test case:
    session_manager.validate_sessions is invoked
    """
    esvs = executor_session_validation_scheduler

    with mock.patch.object(MockAbstractNativeSessionManager,
                           'validate_sessions') as sm_vs:
        sm_vs.return_value = None
        esvs.run()
        sm_vs.assert_called_with()

def test_esvs_disable_session_validation(executor_session_validation_scheduler):
    """
    unit tested:  disable_session_validation

    test case:
    interval is set, so service.stop() will be invoked and enabled = False
    """

    esvs = executor_session_validation_scheduler
    sse = StoppableScheduledExecutor  # from yosai.concurrency
    with mock.patch.object(sse, 'stop') as sse_stop:
        esvs.disable_session_validation()
        sse_stop.assert_called_with() and not esvs.is_enabled

# ----------------------------------------------------------------------------
# AbstractValidatingSessionManager
# ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    'svse,scheduler,scheduler_enabled,expected_result',
    [(True, True, False, True),
     (True, True, True, False),
     (False, True, False, False),
     (True, False, None, True)])
def test_avsm_esvin(abstract_validating_session_manager, monkeypatch,
                    svse, scheduler, scheduler_enabled, expected_result,
                    executor_session_validation_scheduler):
    """
    unit tested:  enable_session_validation_if_necessary

    test case:
    sets a scheduler, defaulting to that from init else enable_session_validation

    I) session_validation_scheduler_enabled = True
       scheduler = self.session_validation_scheduler
       scheduler.enabled = False
   II) session_validation_scheduler_enabled = True
       scheduler = self.session_validation_scheduler
       scheduler.enabled = True
  III) session_validation_scheduler_enabled = False
       scheduler = self.session_validation_scheduler
   IV) session_validation_scheduler_enabled = True
       scheduler = None
    """
    myscheduler = None
    if scheduler:
        myscheduler = executor_session_validation_scheduler
        monkeypatch.setattr(myscheduler, '_enabled', scheduler_enabled)

    avsm = abstract_validating_session_manager
    monkeypatch.setattr(avsm, 'session_validation_scheduler', myscheduler)
    monkeypatch.setattr(avsm, 'session_validation_scheduler_enabled', svse)

    with mock.patch.object(AbstractValidatingSessionManager,
                           'enable_session_validation') as avsm_esv:
        avsm_esv.return_value = None
        avsm.enable_session_validation_if_necessary()
        assert avsm_esv.called == expected_result



def test_avsm_do_validate(abstract_validating_session_manager, mock_session):
    """
    unit tested:  do_validate

    test case:
    basic code path exercise where method is called and successfully finishes
    """
    avsm = abstract_validating_session_manager
    assert avsm.do_validate(mock_session) is None


def test_avsm_do_validate_raises(abstract_validating_session_manager):
    """
    unit tested:  do_validate

    test case:
    session.validate is missing, raising an AttributeError which in turn raises
    IllegalStateException
    """
    avsm = abstract_validating_session_manager

    mock_session = type('DumbSession', (object,), {})()

    with pytest.raises(IllegalStateException):
        avsm.do_validate(mock_session)

def test_avsm_create_svs(abstract_validating_session_manager):
    """
    unit tested: create_session_validation_scheduler

    test case:
    basic codepath exercise that returns a scheduler instance
    """
    avsm = abstract_validating_session_manager
    result = avsm.create_session_validation_scheduler()
    assert isinstance(result, ExecutorServiceSessionValidationScheduler)


def test_avsm_esv_schedulerexists(
    abstract_validating_session_manager,
        executor_session_validation_scheduler, monkeypatch):
    """
    unit tested: enable_session_validation

    test case:
    a scheduler is already set, so no new one is created, and two methods
    called
    """
    avsm = abstract_validating_session_manager
    esvs = executor_session_validation_scheduler

    monkeypatch.setattr(avsm, 'session_validation_scheduler', esvs)

    with mock.patch.object(ExecutorServiceSessionValidationScheduler,
                           'enable_session_validation') as scheduler_esv:
        scheduler_esv.return_value = None
        with mock.patch.object(MockAbstractValidatingSessionManager,
                               'after_session_validation_enabled') as asve:
            asve.return_value = None

            avsm.enable_session_validation()

            scheduler_esv.assert_called_with()
            asve.assert_called_with()

def test_avsm_esv_schedulernotexists(
        abstract_validating_session_manager, monkeypatch,
        patched_abstract_native_session_manager):
    """
    unit tested:  enable_session_validation

    test case:
    no scheduler is set, so a new one is created and set, and then two
    methods called
    """
    avsm = abstract_validating_session_manager
    mock_csvs = mock.MagicMock()
    mock_asve = mock.MagicMock()
    monkeypatch.setattr(avsm, 'create_session_validation_scheduler', mock_csvs)
    monkeypatch.setattr(avsm, 'after_session_validation_enabled', mock_asve)

    avsm.enable_session_validation()
    scheduler_esv = avsm.session_validation_scheduler.enable_session_validation
    assert (scheduler_esv.called and mock_asve.called)


def test_avsm_disable_session_validation_withscheduler_succeeds(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    with a scheduler set, the scheduler's disable_session_validation is called
    and succeeds, and then session_validation_scheduler is set to None
    """
    avsm = abstract_validating_session_manager
    scheduler = ExecutorServiceSessionValidationScheduler

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        with mock.patch.object(scheduler, 'disable_session_validation') as dsv:
            dsv.return_value = None

            sched = scheduler(session_manager=avsm, interval=60)
            monkeypatch.setattr(avsm, 'session_validation_scheduler', sched)

            avsm.disable_session_validation()

            assert (mock_bsvd.called and dsv.called and
                    avsm.session_validation_scheduler is None)

def test_avsm_disable_session_validation_withscheduler_fails(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    with a scheduler set, the scheduler's disable_session_validation is called
    and fails, and then session_validation_scheduler is set to None
    """
    avsm = abstract_validating_session_manager

    scheduler = ExecutorServiceSessionValidationScheduler

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        with mock.patch.object(scheduler, 'disable_session_validation') as dsv:
            dsv.side_effect = AttributeError

            sched = scheduler(session_manager=avsm, interval=60)
            monkeypatch.setattr(avsm, 'session_validation_scheduler', sched)

            avsm.disable_session_validation()

            assert (mock_bsvd.called and dsv.called and
                    avsm.session_validation_scheduler is None)


def test_avsm_disable_session_validation_without_scheduler(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  disable_session_validation

    test case:
    without a scheduler set,  only before_session_validation_disabled is called
    """
    avsm = abstract_validating_session_manager

    with mock.patch.object(MockAbstractValidatingSessionManager,
                           'before_session_validation_disabled') as mock_bsvd:
        mock_bsvd.return_value = None

        avsm.disable_session_validation()

        assert mock_bsvd.called and avsm.session_validation_scheduler is None


def test_avsm_validate_sessions_raises(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  validate_sessions

    test case:
    get_active_sessions() is called, returning a list containing THREE sessions
        - the first session succeeds to validate
        - the second session raises ExpiredSessionException from validate
        - the third session raises StoppedSessionException from validate
    """
    avsm = abstract_validating_session_manager

    valid_session = mock.MagicMock()
    expired_session = mock.MagicMock()
    stopped_session = mock.MagicMock()
    expired_session.validate.side_effect = ExpiredSessionException
    stopped_session.validate.side_effect = StoppedSessionException
    active_sessions = [valid_session, expired_session, stopped_session]

    monkeypatch.setattr(avsm, 'get_active_sessions', lambda: active_sessions)

    with mock.patch('yosai.DefaultSessionKey') as dsk:
        dsk.return_value = 'sessionkey123'
        results = avsm.validate_sessions()
        assert '[2] sessions' in results

def test_avsm_validate_sessions_allvalid(
        abstract_validating_session_manager, monkeypatch):
    """
    unit tested:  validate_sessions

    test case:
    get_active_sessions() is called, returning a list containing TWO sessions
        - the first session succeeds to validate
        - the second session succeeds to validate
    """
    avsm = abstract_validating_session_manager

    valid_session1 = mock.MagicMock()
    valid_session2 = mock.MagicMock()

    active_sessions = [valid_session1, valid_session2]

    monkeypatch.setattr(avsm, 'get_active_sessions', lambda: active_sessions)

    with mock.patch('yosai.DefaultSessionKey') as dsk:
        dsk.return_value = 'sessionkey123'
        results = avsm.validate_sessions()
        assert 'No sessions' in results

# ----------------------------------------------------------------------------
# DefaultSessionManager
# ----------------------------------------------------------------------------


def test_dsm_new_session_instance(mock_default_session_manager, monkeypatch):
    """
    unit tested:  new_session_instance

    test case:
    basic code path exercise-- creates a session instance and returns it
    """
    mdsm = mock_default_session_manager

    monkeypatch.setattr(mdsm.session_factory,
                        'create_session',
                        lambda x: 'tested')

    result = mdsm.new_session_instance('sessioncontext')

    assert result == 'tested'

def test_dsm_create(mock_default_session_manager, monkeypatch):
    """
    unit tested:  create

    test case:
    relays session to session_store's create method
    """
    mdsm = mock_default_session_manager

    with mock.patch.object(MemorySessionStore, 'create') as msd_create:
        msd_create.return_value = None
        mdsm.create('session')
        msd_create.assert_called_once_with('session')

def test_dsm_on_stop_using_simplesession(
        mock_default_session_manager, simple_session, monkeypatch):
    """
    unit tested:  on_stop

    test case:
    when passing a simplesession as a parameter, the last_access_time gets
    updated in it and then on_change is called
    """
    mdsm = mock_default_session_manager
    stopped = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    monkeypatch.setattr(simple_session, 'stop_timestamp', stopped)
    with mock.patch.object(MockDefaultNativeSessionManager, 'on_change') as mdsm_oc:
        mdsm_oc.return_value = None
        mdsm.on_stop(simple_session)
        mdsm_oc.assert_called_once_with(simple_session)
        assert simple_session.last_access_time == stopped

def test_dsm_on_stop_notusing_complete_simplesession(
        mock_default_session_manager, simple_session, monkeypatch):
    """
    unit tested:  on_stop

    test case:
    no last_access_time attribute exists, raising an exception but handling
    gracefully, and ultimately calling on_change
    """
    mdsm = mock_default_session_manager
    monkeypatch.delattr(simple_session, '_stop_timestamp')
    with mock.patch.object(MockDefaultNativeSessionManager, 'on_change') as mdsm_oc:
        mdsm_oc.return_value = None
        mdsm.on_stop(simple_session)
        mdsm_oc.assert_called_once_with(simple_session)

def test_dsm_get_session_id(mock_default_session_manager):
    """
    unit tested:  get_session_id

    test case:
    passthrough call to session_key
    """
    mdsm = mock_default_session_manager

    class SessionKey:
        def __init__(self):
            self.session_id = '12345'

    sk = SessionKey()

    result = mdsm.get_session_id(sk)

    assert result == '12345'


def test_dsm_rsfds(mock_default_session_manager, monkeypatch):
    """
    unit tested:  retrieve_session_from_data_source

    test case:
    passthrough call to session_store.read_session
    """

    mdsm = mock_default_session_manager
    monkeypatch.setattr(mdsm.session_store, 'read_session', lambda x:  'session')
    result = mdsm.retrieve_session_from_data_source('sessionid123')

    assert result == 'session'



@pytest.mark.parametrize('active_sessions, expected',
                         [(('session1', 'session2'), ('session1', 'session2')),
                          (None, tuple())])
def test_dsm_getactivesessions(
        mock_default_session_manager, monkeypatch, active_sessions, expected):
    """
    unit tested:  get_active_sessions

    test case:
    returns either an empty tuple or a tuple of active sessions
    """
    mdsm = mock_default_session_manager
    monkeypatch.setattr(mdsm.session_store, 'get_active_sessions', lambda: active_sessions)
    result = mdsm.get_active_sessions()
    assert result == expected
