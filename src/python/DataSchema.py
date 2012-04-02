from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Auth import authz_match
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import *
from SiteDB.Regexps import *
from operator import itemgetter
from os.path import join as joinpath
import os, string, random

def mkpasswd():
  """Utility to generate new passwords for roles."""
  passchars = string.letters + string.digits
  return ''.join(random.choice(passchars) for _ in xrange(10))

class Schema(RESTEntity):
  """REST entity which represents the SiteDB schema in the database, both
  the schema currently in the selected database instance, and the reference
  schema in ``$PWD/src/sql/sitedb.sql``.

  In a database, a schema usually corresponds to a *master account* possibly
  but not necessarily associated with related *reader and writer* accounts.
  Production databases have all three accounts, private development ones may
  have all three but often just the master account. The master account owns
  the schema and the data; it is not used for web services outside the admin
  operations. If present, the reader account can read but not modify the data
  nor the schema, and the writer account can update data but not the schema.

  All admin operations on the schema are performed on the master account. If
  the class detects the auxiliary accounts are present, it adjusts the schema
  commands suitably. When present the auxiliary accounts are granted suitable
  read and update privileges against the master schema. There are no admin
  commands to run against the reader or writer accounts: they are only used
  for authentication alias to the master schema, there are no schema objects
  such as synonyms under the auxiliary accounts. :class:`~.DBConnectionPool`
  will explicitly set the *current schema* attribute on connections to the
  master. This avoids having to prefix object names in SQL statements, and
  on the other hand avoids maintaining synonyms under auxiliary accounts.

  In each master instance there can be two schemas live at any one time: the
  *current* and *archive* schemas. Normally only the current one exists. When
  a migration requires major surgery on the schema, not implementable with
  online incremental changes, the current schema is moved entirely out of the
  way, i.e. archived, and a new current schema is created in place. During
  this operation all the names of all the database objects are changed so as
  not to collide with any new schema to be loaded. Once the new schema has
  been loaded, the archived contents are copied to the new schema, and the
  new schema and contents are validated and the archive schema and data are
  backed up then removed. For each release requiring schema migration this
  class is modified to apply the necessary operations automatically, possibly
  assisted with additional SQL command files under ``src/sql``.

  A HTTP GET will retrieve canonical version of the schema currently in the
  database, to the extent that is possible (read: everything except role
  passwords will be blinded out).

  A HTTP PUT will insert a new schema into the database. The target database
  must not have any current schema in it; any existing schema must first be
  eliminated with POST (= archived) or DELETE (= removed).

  A HTTP POST will archive current schema or restore an archived schema.

  A HTTP DELETE will remove an archived or current schema, or both.

  This REST entity is only used as an embedded internal web service within
  admin operation commands (cf. :command:`sitedb-admin`). It's obviously
  not included in the normal running web server.

  This class expects to find in ``$PWD/src/sql/sitedb.sql`` the current
  reference schema. The file is parsed into individual schema statements at
  construction time. The file may contain "``-- comments``" and individual
  schema statements separated with semi-colons. The statements are executed
  in the order they appear in the file when creating a new schema.

  .. warning::

     The current SiteDB schema lacks many features one would normally expect,
     for example it's very loose on constraints. While you can use this class
     as an example, do **not** use the actual SiteDB schema as an example.

  .. note::

     Normally when testing a new schema, one should dump the current schema
     from a production database and the test schema from test database using
     the GET operation, and compare the results, in addition to comparing SQL
     files. This avoids nasty surprises in case of rogue database maintenance,
     and in case some particular aspects has been forgotten.

  .. note::

     Specifying schema explicitly on connect also seems to avoid certain past
     bugs with server side cursor sharing when multiple instances of the same
     schema exist within the same database, and cursors accidentally get
     shared among them, and a client supposedly running against one instance
     accidentally updates contents some other (wrong) instance. While the bugs
     have reportedly been fixed, they've resurfaced several times. Apparently
     explicitly specifying schema helps stay clear of them.

  .. note::

     This class does also support using *roles* for finer grained access
     privileges, although they are not currently used with SiteDB. If roles
     were enabled, the writer account alone would be granted no or limited
     update privileges and clients would enable separate roles to gain actual
     write access to specific parts of the database. This allows different
     clients to share the same database account but be given varying degree
     of privileges to the tables. The longer-term plan is to use this feature
     to grant the web site write access only to parts of the database, and the
     hypernews synchronisation restricted access to only the tables it needs.

  .. note::

     The "legacy" SiteDB accounts have not been set up using this tool, and
     do not fully conform to the above description. No schema SQL file has
     survived for the schema present in the database; the one in ``src/sql``
     was reverse engineered from database dumps. There are currently synonyms
     under auxiliary accounts; they are unused by this server since it sets
     current schema on connect. The tables haven't been uniformly given the
     necessary grants, so in practice only the writer account is actually
     usable. At the time we migrate to SiteDB V2 in production, all these
     will be corrected by reinitialising the schema using this class.
  """

  def __init__(self, *args):
    RESTEntity.__init__(self, *args)
    self._schemadir = joinpath(os.getcwd(), "src/sql")
    self._schema = open(joinpath(self._schemadir, "sitedb.sql")).read()

  def validate(self, apiobj, method, api, param, safe):
    """Validate request input data."""
    if method == 'POST':
      validate_str('action', param, safe, re.compile(r"^(archive|restore)$"))
    elif method == 'DELETE':
      validate_str('action', param, safe, re.compile(r"^(all|archive|current)$"))

    authz_match(role=["Global Admin"], group=["global"])

  @restcall
  @tools.expires(secs=3600)
  def get(self):
    """Retrieve a canonical schema description from the database.

    The dump produced is guaranteed to be deterministic but note that it will
    not look like the reference ``$PWD/src/sql/sitedb.sql`` schema. In order
    to compare schema in different databases with the reference, first load
    the reference into another database, dump the schema for all, and compare
    the outputs with ``diff``.

    The output is structured so that it should be possible to load it directly
    into a database as a schema script. For example the output includes all
    tables first followed by foreign keys such that when one table references
    another both have already been mentioned in the output. The tables are
    *not* output in the order they appear in the reference, typically output
    order is alphabetical per object category.

    If the database contains roles associated with this schema, the passwords
    will be blinded out as ``FAKE_randomstring_FAKE``. If you use this dump for
    backup, on restore you need to change the passwords back to originals. DBA
    privileges would be required to recover the original (hashed) passwords.

    :return: Sequence of strings representing the entire schema."""
    rows = []
    statements = [
      # Configure DBMS_METADATA. BEGIN ... END avoids PL/SQL procedure bind.
      # NOTE: If SiteDB schema acquires storage specs, switch them on here!
      "begin"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'PRETTY', true);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'STORAGE', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'TABLESPACE', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'SQLTERMINATOR', true);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'REF_CONSTRAINTS', false);"
      " dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'CONSTRAINTS_AS_ALTER', false);"
      "end;",

      # Retrieve tables, but not backing tables for materialized views. Get
      # tables without referential constraints because we cannot control the
      # order in which tables are retrieved, so we need to prevent foreign
      # key declarations to tables which don't even exist yet.
      "select dbms_metadata.get_ddl('TABLE', x.object_name) from user_objects x"
      " where object_type = 'TABLE' and not exists (select 1 from user_objects o"
      " where o.object_name = x.object_name and o.object_type = 'MATERIALIZED VIEW')"
      " order by x.object_name",

      # Get all normal indices. Indices created by constraints were already
      # covered above as table constraints so we exclude them here.
      "select dbms_metadata.get_ddl('INDEX', x.index_name) from user_indexes x"
      " where not exists (select 1 from user_constraints c where"
      " c.constraint_name = x.index_name and c.table_name = x.table_name)"
      " order by x.index_name",

      # Fetch rest of object creation clauses.
      "select dbms_metadata.get_ddl(replace(object_type, ' ', '_'), object_name)"
      " from user_objects where object_type in ('SEQUENCE', 'PROCEDURE', 'PACKAGE',"
      " 'PACKAGE BODY', 'MATERIALIZED VIEW', 'VIEW', 'FUNCTION', 'TRIGGER', 'SYNONYM')"
      " order by object_type, object_name",

      # Now create DDL for foreign key referential constraints, targets exist.
      "select dbms_metadata.get_dependent_ddl('REF_CONSTRAINT', table_name) from"
      " (select distinct table_name from user_constraints where constraint_type = 'R')"
      " order by table_name",

      # Finally, dump database links. Annnoyingly the get_ddl() argument name
      # differs from user_objects.object_type so handle this separately.
      "select dbms_metadata.get_ddl('DB_LINK', object_name)"
      " from user_objects where object_type = 'DATABASE LINK'"
      " order by object_name",

      # Retrieve roles. Attempting to access roles directly with get_ddl('ROLE')
      # does not work because the information is only available to DBAs. Expand
      # the DDL manufacturing statements manually, it's not so much.
      "select 'CREATE ROLE ' || granted_role || ' IDENTIFIED BY @PASSWORD@;'"
      " from user_role_privs where admin_option = 'YES'",

      "select 'GRANT ' || privilege || ' TO ' || role ||"
      " (case when admin_option = 'YES' then ' WITH ADMIN OPTION;' else ';' end)"
      " from role_sys_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      "select 'GRANT ' || granted_role || ' TO ' || role ||"
      " (case when admin_option = 'YES' then ' WITH ADMIN OPTION;' else ';' end)"
      " from role_role_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      "select 'GRANT ' || privilege || ' ON \"' || owner || '\".\"'"
      " || table_name || '\" TO ' || role ||"
      " (case when grantable = 'YES' then ' WITH GRANT OPTION;' else ';' end)"
      " from role_tab_privs where role in (select granted_role from user_role_privs"
      " where admin_option = 'YES')",

      # Now dump object and system grants plus default role. These generate
      # 'ORA-31608: specified object of type XYZZY not found' if there is no
      # information available of the given type, requiring protection below.
      "select dbms_metadata.get_dependent_ddl('OBJECT_GRANT', x.object_name,"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from user_objects x"
      " where x.object_type != 'INDEX'",

      "select dbms_metadata.get_granted_ddl('SYSTEM_GRANT',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      "select dbms_metadata.get_granted_ddl('DEFAULT_ROLE',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      "select dbms_metadata.get_granted_ddl('ROLE_GRANT',"
      " sys_context('USERENV', 'CURRENT_SCHEMA')) from dual",

      # Restore DBMS_METADATA settings.
      "begin dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'DEFAULT'); end;"
    ]

    # Run all statements, and collect any data they produced. If there are
    # any CLOBs from dbms_metadata.get_ddl() type calls, read them in. Fake
    # out passwords from roles with template contents.
    #
    # If we come across "IDENTIFIED BY @PASSWORD@", generate a password.
    # If we got to sys.user$ / dba_roles tables, we could add "IDENTIFED
    # BY VALUES 'xxx'" but we can't get at original hashed passwords, so
    # just fake new passwords for all roles.
    for stmt in statements:
      try:
        c, _ = self.api.execute(stmt)
        if stmt.startswith("select"):
          for text, in c:
            if hasattr(text, 'read'):
              text = text.read()
            while text.upper().find("IDENTIFIED BY @PASSWORD@") >= 0:
              text = text.replace("@PASSWORD@", "FAKE_" + mkpasswd() + "_FAKE", 1)
            rows.append(text)
      except Exception, e:
	# Ignore ORA-31608: specified object of type XYZZY not found
	if not e.args or getattr(e.args[0], 'code', None) != 31608:
	  raise

    return rows

  @restcall
  def post(self, action):
    """Update database schema, i.e. archive current schema out of the way
    or restore archived schema back to main schema.

    The database must contain a schema previously initialised with PUT.
    This operation moves all tables, sequences, indices and constraints
    out of the way by renaming them with a prefix ``X`` (action=archive)
    or removing the prefix ``X`` (action=restore).

    The caller must have global admin privileges.

    :arg str action: update action to perform.
    :returns: series of messages on what was renamed."""
    rows = []
    if action == 'save':
      negate = 'not'
      rename = lambda old: "X%s" % old[0:29]
    elif action == 'restore':
      negate = ''
      rename = lambda old: old[1:]
    else:
      raise RuntimeError("Internal error, invalid 'action'")

    # Rename tables and sequences.
    c, _ = self.api.execute("select object_type, object_name from user_objects"
		            " where object_type in ('TABLE', 'SEQUENCE')"
                            "  and object_name %s like 'X%%'" % negate)
    for type, old_name in c:
      new_name = rename(old_name)
      rows.append("Renaming %s %s to %s" % (type, old_name, new_name))
      self.api.execute("rename %s to %s" % (old_name, new_name))

    # Rename constraints.
    c, _ = self.api.execute("select constraint_name, table_name "
                            "from user_constraints "
		            "where constraint_name %s like 'X%%' "
			    "  and constraint_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter table %s rename constraint %s to %s"
		       % (table_name, old_name, new_name))

    # Rename non-constraint indices.
    c, _ = self.api.execute("select index_name, table_name "
                            "from user_indexes "
		            "where index_name %s like 'X%%' "
			    "  and index_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming index %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter index %s rename to %s" % (old_name, new_name))

    # Rename triggers.
    c, _ = self.api.execute("select trigger_name, table_name "
                            "from user_triggers "
		            "where trigger_name %s like 'X%%' "
			    "  and trigger_name not like 'SYS%%'" % negate)
    for old_name, table_name in c:
      new_name = rename(old_name)
      rows.append("Renaming trigger %s [%s] to %s" % (old_name, table_name, new_name))
      self.api.execute("alter trigger %s rename to %s" % (old_name, new_name))

    return rows

  @restcall
  def put(self):
    """Insert database schema.

    The database must be previously empty, either not have any schema at all,
    or have the existing schema moved out of the way with a POST. This must
    be executed for the master admin account. If the current database object
    has multiple accounts, automatically also installs grants for reader and
    writer accounts.

    The caller must have global admin privileges.

    :returns: a simple 'ok' object on success; if the schema contains roles,
              the 'ok' is preceded by dictionaries with role/password pairs."""
    rows = []
    for stmt in self._schema.split(";"):
      while stmt.upper().find("IDENTIFIED BY @PASSWORD@") >= 0:
        passwd = mkpasswd()
        rows.append({ stmt: passwd })
        stmt = stmt.replace("@PASSWORD@", passwd, 1)
      self.api.execute(stmt)

    # Get all objects requiring grants, existing roles (created above),
    # and possible foo_reader/foo_writer accounts for current account.
    c, _ = self.api.execute("select object_name from user_objects"
                            " where object_type in ('TABLE', 'SEQUENCE')")
    objs = [o for o, in c]

    c, _ = self.api.execute("select granted_role from user_role_privs"
                            " where admin_option = 'YES'")
    roles = [r for r, in c]

    c, _ = self.api.execute("select username from all_users"
		            " where username = sys_context('userenv', 'session_user') || '_READER'"
			    "    or username = sys_context('userenv', 'session_user') || '_WRITER'")
    accts = [a for a, in c]
    reader = [a for a in accts if a.endswith("_READER")]
    writer = [a for a in accts if a.endswith("_WRITER")]

    # Grant all roles to the writer account, if any.
    if writer:
      for role in roles:
        self.api.execute("grant %s to %s" % (role, writer[0]))

    # Revoke all grants on all objects, then grant read access to the
    # reader and writer accounts, and update rights to specific roles
    # to be used inside the writer account. The current account keeps
    # all privileges on everything.
    for obj in objs:
      for role in reader + writer + roles:
        self.api.execute("revoke all on %s from %s" % (obj, role))
      for role in reader + writer:
        self.api.execute("grant select on %s to %s" % (obj, role))
      if writer:
        for role in roles:
	  if role == "SITEDB_WEBSITE":
	    if obj.startswith('TIER') or obj.startswith('CRYPT') or obj.startswith('CONTACT'):
              pass
	    elif obj.startswith('RESOURCE_PLEDGE') or obj.startswith('RESOURCE_DELIVERED'):
              self.api.execute("grant insert, select on %s to %s" % (obj, role))
	    else:
              self.api.execute("grant delete, insert, select, update on %s to %s" % (obj, role))

    rows.append('ok')
    return rows

  @restcall
  def delete(self, action):
    """Delete database schema, either all of it, or the current one, or
    a previously archived schema.

    The database must contain a schema previously intialised with PUT.
    The operation removes all tables, sequences, indices and constraints
    by truly deleting them, unlike POST which just archives them. The
    possible actions are ``all`` to delete everything, ``current`` to
    delete the current production schema but leave archived one in place,
    or ``archive`` to delete archived schema (objects with prefix ``X``)
    and leave current production schema alone.

    The caller must have global admin privileges.

    :arg str action: delete action to perform.
    :returns: a simple 'ok' object on success."""
    some_objs = ['SEQUENCE', 'MATERIALIZED VIEW', 'VIEW', 'TABLE',
		 'INDEX', 'SYNONYM', 'TRIGGER']
    more_objs = ['FUNCTION', 'PROCEDURE', 'PACKAGE', 'PACKAGE BODY']
    if action == 'all':
      condition = " where object_type in (%s)" % \
        ", ".join(["'%s'" % x for x in some_objs + more_objs])
    elif action == 'current' or action == 'archive':
      negation = (action == 'current' and 'not') or ''
      condition = " where object_type in (%s) and object_name %s like 'X%%'" % \
        (", ".join(["'%s'" % x for x in some_objs]), negation)
    else:
      raise RuntimeError("Internal error, invalid 'action'")

    rows = []
    for type in types:
      c, _ = self.api.execute("select object_type, object_name"
                              " from user_objects%s" % condition)
      for type, name in c:
        rows.append("Dropping %s %s" % (type, name))
	cascade = (type == 'TABLE' and ' cascade constraints') or ''
        self.api.execute("drop %s %s%s" % (type, name, cascade))

    if action == 'all':
      c, _ = self.api.execute("select granted_role from user_role_privs"
			      " where admin_option = 'YES'")
      for name, in c:
        rows.append("Dropping ROLE %s" % name)
        self.api.execute("drop role %s" % name)

    return rows
