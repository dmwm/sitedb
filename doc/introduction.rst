Introduction
============

To make a call to any of the SiteDB v2 APIs, you need to have a CMS VO certificate or proxy.

The APIs available are: ``whoami``, ``roles``, ``groups``, ``people``, ``sites``, ``site-names``, ``site-resources``, ``site-associations``, ``resource-pledges``, ``pinned-software``, ``site-responsibilities``, ``group-responsibilities``.

For example: ::

   $ curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/people?match=diego"
   {"desc": {"columns": ["username", "email", "forename", "surname", "dn", "phone1", "phone2", "im_handle"]}, "result": [
    ["diego", "diego@cern.ch", "Diego", "da Silva Gomes", "/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253", "+41 76 602 0801", "+41 22 76 76093", "gtalk:geneguvo@gmail.com"]
   ]}

   $ curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/whoami"
   {"result": [
    {"dn": "/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253", "login": "diego", "method": "X509Proxy", "roles": {"global-admin": {"group": ["global"], "site": []}, "-admin": {"group": ["couchdb"], "site": []}}, "name": "Diego da Silva Gomes"}
   ]}

Or access the URLs directly from a browser where your certificate is properly configured, for instance `<https://cmsweb.cern.ch/sitedb/data/prod/whoami>`_. Note, however, that when accessing from the browser you'll get the output in the XML format.

You can choose between output formats by setting the *Accept* HTTP header in the request: ``Accept: application/json``, ``Accept: application/xml`` or ``Accept: */*`` (defaults to JSON). Since browsers use something like ``text/html,application/xhtml+xml,application/xml``, you get a XML as output. Curl by default uses ``Accept: */*`` and therefore you get a JSON output. You can use the ``-H "Accept: application/xml"`` with curl to get the response in XML.

Also note that some APIs output a description of the columns as the first line, where others don't. Compare, for instance, the two curl example calls to ``people`` and ``whoami`` shown above. The ``people`` call shows ``"desc": {"columns": ["username", "email", "forename", "surname", "dn", "phone1", "phone2", "im_handle"]}`` before the result, where ``whoami`` does not.

Finally, on your API calls you can choose between the *production* and the *development* databases by using ``prod`` and ``dev`` respectively in the URL path. The examples above query ``prod``. It is recommended you use ``dev`` while you are testing yours scripts or any write API calls to avoid any harm to the production instance in case of bugs or mistakes. Once you are happy enough with the tests, then change the URL to ``prod``. There is no guarantee that ``dev`` will match what's in ``prod`` even though we clone ``prod`` to ``dev`` every once in a while. On the contrary, ``dev`` normally contains a bunch of dummy data you can play with.
