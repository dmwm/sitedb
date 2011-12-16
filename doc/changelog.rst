SiteDB release notes
====================

2.1.0
-----

.. rubric:: SiteDB web site

This version adds a complete V2 web site browsing interface, but still
without update functionality.

.. rubric:: Database-related improvements

Database connection management has been rewritten. The server has been
tested to gracefully degrade and autonomously recover from various kinds
of network and database outages, but not yet an outright database server
lock-up/fault event. Connections are no longer created at server start,
allowing the server to start even if database is unavailable.

The SiteDB database schema is now represented by REST entities, allowing
complete self-bootstrap through an administrative REST API. A command
line ``sitedb-admin`` tool interfaces to the admin API. The admin parts
are obviously not a part of the regular web server installation.

The server now logs database connection statistics on SIGUSR2 signal.

.. rubric:: HTTP level improvements

Each API can now specify the valid MIME types for an Accept header
using :py:func:`restcall` ``formats`` keyword option. There is now
:py:class:`RawFormat` formatter for streaming images. The error for
a missing or inappropriate Accept request header is now better.

The server now honours "Accept-Encoding: deflate" request header.
:py:class:`~.MiniRESTApi` ``compression``, ``compression_level`` and
``compression_chunk`` attributes set the defaults but which
:py:func:`~.restcall` keyword options can override per entity method.

The server now generates ETag differently. The ETag is now output in
normal headers for most responses, and the server correctly processes
any If-Match, If-None-Match request headers. Responses exceeding the
:py:attr:`~.MiniRESTApi.etag_limit` threshold are still streamed out,
with ETag generated as a trailer header and If-Match, If-None-Match
processing omitted. ETag is generated with :py:class:`~.SHA1ETag` by
default; ``etagger`` option overrides the choice. Tagging works also
for ``serve_file()`` responses.

The server now interacts better with caches. Response expiration set
with :py:data:`~.expires` tool or :py:func:`~.restcall` ``expires``
keyword option are translated to an appropriate Cache-Control header.
Extra directives may be added per entity using ``expires_opts`` with
:py:func:`~.restcall`. The server now outputs correct Vary header,
notably for Accept and Accept-Encoding request headers.

.. rubric:: General server improvements

:py:func:`~.restcall` decorator can now be used with keyword arguments.

There is now an intermediate :py:class:`~.RESTApi` class for
non-database entity-based REST servers.

Logging was improved. Access log includes incoming and outgoing bytes,
and the logger is careful not to try printing values not yet set in
requests failing early in the processing. Database errors include the
instance name, and debug tracing of database activity is much improved.
Client dropping a connection early will no longer trigger noisy errors
from the chunk producer. The proper JSON/XML trailer is output even if
an entity raises an exception.

There is a reasonably complete test suite for the core REST server. A
new server configuration ``silent`` option silences start-up messages,
mainly for the test suite.

.. rubric:: Development improvements

Better API documentation. ``setup.py`` supports options ``--skip-docs``
and ``--compress`` to skip the documentation build and to minimise HTML,
CSS and JavaScript, respectively. Using ``--compress`` triggers output
of a production web site, omitting it generates a very debuggable site.

2.0.0
-----

This is a bare bones version implementing basic REST data access API,
with only minimal -- and non-functional -- user interface.
