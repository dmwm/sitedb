Introduction
============

To make a call to any of the SiteDB v2 APIs, you need to have a CMS VO
certificate or proxy.

The APIs available are: ``whoami``, ``roles``, ``groups``, ``people``,
``sites``, ``site-names``, ``site-resources``, ``site-associations``,
``resource-pledges``, ``pinned-software``, ``site-responsibilities``,
``group-responsibilities``, ``federations``, ``federations-sites``,
``federations-pledges``, ``esp-credit``.

For example: ::

   $ curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/people?match=diego"
   {"desc": {"columns": ["username", "email", "forename", "surname", "dn", "phone1", "phone2", "im_handle"]}, "result": [
    ["diego", "diego@cern.ch", "Diego", "da Silva Gomes", "/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253", "+41 76 602 0801", "+41 22 76 76093", "gtalk:geneguvo@gmail.com"]
   ]}

   $ curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/whoami"
   {"result": [
    {"dn": "/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253", "login": "diego", "method": "X509Proxy", "roles": {"global-admin": {"group": ["global"], "site": []}, "-admin": {"group": ["couchdb"], "site": []}}, "name": "Diego da Silva Gomes"}
   ]}

Or access the URLs directly from a browser where your certificate is
properly configured, for instance
`<https://cmsweb.cern.ch/sitedb/data/prod/whoami>`_. Note, however, that
when accessing from the browser you'll get the output in the XML format.

You can choose between output formats by setting the *Accept* HTTP header
in the request: ``Accept: application/json``, ``Accept: application/xml``
or ``Accept: */*`` (defaults to JSON). Since browsers use something like
``text/html,application/xhtml+xml,application/xml``, you get a XML as
output. Curl by default uses ``Accept: */*`` and therefore you get a
JSON output. You can use the ``-H "Accept: application/xml"`` with
curl to get the response in XML.

Also note that some APIs output a description of the columns as the
first line, where others don't. Compare, for instance, the two curl
example calls to ``people`` and ``whoami`` shown above. The ``people``
call shows ``"desc": {"columns": ["username", "email", "forename",
"surname", "dn", "phone1", "phone2", "im_handle"]}`` before the
result, where ``whoami`` does not.


On your API calls you can choose between the *production* and the
*development* databases by using ``prod`` and ``dev`` respectively in
the URL path. The examples below query ``prod``. It is recommended you
use ``dev`` while you are testing yours scripts or any write API calls
to avoid any harm to the production instance in case of bugs or mistakes.
Once you are happy enough with the tests, then change the URL to ``prod``.
There is no guarantee that ``dev`` will match what's in ``prod`` even
though we clone ``prod`` to ``dev`` every once in a while. On the
contrary, ``dev`` normally contains a bunch of dummy data you can
play with.


API calls examples
------------------

1. whoami
~~~~~~~~~

 Return information on the calling user. The user description contains
 the following fields. All the information is always present, regardless
 of authentication method. Data not known will be null, for example if
 access is made using CMS VO X509 certificate which is not registered
 in SiteDB, much of the information will be empty.


 Curl example: ::
 
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/whoami"
   {"result": [
   {"dn": "/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=jbalcas/CN=751133/CN=Justas Balcas", "login": "jbalcas", "method": "X509Proxy", "roles": {}, "name": "Justas Balcas"}]}

 URL : `<https://cmsweb.cern.ch/sitedb/data/prod/whoami>`_

 Browser output example: ::

    <sitedb>
       <result>
          <dict>
             <key>dn</key>
             <value>/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=jbalcas/CN=751133/CN=Justas Balcas</value>
             <key>login</key>
             <value>jbalcas</value>
             <key>method</key>
             <value>X509Cert</value>
             <key>roles</key>
             <value>
                <dict></dict>
             </value>
             <key>name</key>
             <value>Justas Balcas</value>
          </dict>
       </result>
    </sitedb>
            
 ``name``  - The full name.

 ``login`` - CERN account.

 ``dn``    - X509 certificate distinguished name.

 ``method``
  Authentication method, one of ``X509Cert``, ``X509Proxy``, ``HNLogin``,
  HostIP``, ``AUCookie`` or ``None``. In practice for SiteDB it will
  only be one of the first two since the latter three are not allowed
  authentication methods for SiteDB and this REST entity.

 ``roles``
  A dictionary of authorisation roles possessed by the user. For each
  role the person has, there will be a key-value pair where the key is
  the *canonical* role name, and the value is another dictionary with
  keys ``group`` and ``site``, each of whose value is a list. The lists
  will contain the *canonical* group and site names for which the role
  applies, respectively. Canonical names are all lower-case, with all
  word delimiters replaced with a single dash. For example the canonical
  role title for "Global Admin" is "global-admin", and for the site
  "T1\_CH\_CERN" it is "t1-ch-cern".

2. roles
~~~~~~~~
   
 Return information abot existing roles in SiteDB.
    
 URL : `<https://cmsweb.cern.ch/sitedb/data/prod/roles>`_

 Curl example: ::
  
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/roles"
   {"desc": {"columns": ["title"]}, "result": [
   ["Admin"]
   ,["CRAB Server Operator"]
   ,["DBSExpert"]
   ,["Data Manager"]
   ,["Developer"]
   ,["DocDB Admin"]
   ,["FTS Contact"]
   ,["Global Admin"]
   ,["GlobalTag Manager"]
   ,["Operator"]
   ,["PADA Admin"]
   ,["PhEDEx Contact"]
   ,["Production Manager"]
   ,["Production Operator"]
   ,["ProductionAccess"]
   ,["Results Service"]
   ,["Site Admin"]
   ,["Site Executive"]
   ,["StageManager"]
   ,["StageRequest"]
   ,["T0 Operator"]
   ,["_admin"]
   ,["web-service"]
   ]}

 Browser output example: ::
     
     <sitedb>
        <desc>
           <dict>
              <key>columns</key>
              <value>
                 <array>
                    <i>title</i>
                 </array>
              </value>
          </dict>
        </desc>
        <result>
           <array>
              <i>Admin</i>
           </array>
           <array>
              <i>CRAB Server Operator</i>
           </array>
           <array>
              <i>DBSExpert</i>
           </array>
           <array>
              <i>Data Manager</i>
           </array>
           ...
           <array>
              <i>web-service</i>
           </array>
        </result>
    </sitedb>

 ``title`` - Role name.


3. groups
~~~~~~~~~
            
 Return information about existing groups in SiteDB.

 URL : `<https://cmsweb.cern.ch/sitedb/data/prod/groups>`_

 Curl example: ::
   
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/groups"
   {"desc": {"columns": ["name"]}, "result": [
   ["ASO"]
   ,["CondDB"]
   ,["CouchDB"]
   ,["DAS"]
   ,["DBS"]
   ,["DataOps"]
   ,["DataQuality"]
   ,["FacOps"]
   ,["IB RelVal"]
   ,["ReqMgr"]
   ,["SiteDB"]
   ,["alertscollector"]
   ,["caf-alca"]
   ,["caf-comm"]
   ,["caf-lumi"]
   ,["caf-phys"]
   ,["ewk"]
   ,["global"]
   ,["higgs"]
   ,["phedex"]
   ,["site"]
   ,["top"]
   ]}

 Browser output example: ::
  
    <sitedb>  
       <desc>
          <dict>
             <key>columns</key>
             <value>
                <array>
                   <i>name</i>
                </array>
             </value>
          </dict>
       </desc>
       <result>
          <array>
             <i>ASO</i>
          </array>
          <array>
             <i>CondDB</i>
          </array>
          <array>
             <i>CouchDB</i>
          </array>
          ...
          <array>
             <i>top</i>
          </array>
       </result>
    </sitedb>

 ``name`` - group name.
  
4. people
~~~~~~~~~

 Retrieve people. All the information is always present. In query
 you can add ?match=**** , where ``****`` must be replaced to username.

 URL : `<https://cmsweb.cern.ch/sitedb/data/prod/people>`_

 Curl example: ::
   
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/people"
   ``Will give you all present people in sitedb.``
      
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/people?match=diego"
   {"desc": {"columns": ["username", "email", "forename", "surname", "dn", "phone1", "phone2", "im_handle"]}, "result": [
   ["diego", "diego.da.silva.gomes@cern.ch", "Diego", "Da Silva Gomes", "/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253", "+41 76 602 0801", "+41 22 76 76093", "gtalk:geneguvo@gmail.com"]
   ]}

   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/people?match=jbalcas"
   {"desc": {"columns": ["username", "email", "forename", "surname", "dn", "phone1", "phone2", "im_handle"]}, "result": [
   ["jbalcas", "justas.balcas@cern.ch", "Justas", "Balcas", "/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=jbalcas/CN=751133/CN=Justas Balcas", null, null, null]
   ]}

 Browser output example: ::

    <sitedb>
       <desc>
          <dict>
             <key>columns</key>
             <value>
                <array>
                   <i>username</i>
                   <i>email</i>
                   <i>forename</i>
                   <i>surname</i>
                   <i>dn</i>
                   <i>phone1</i>
                   <i>phone2</i>
                   <i>im_handle</i>
                </array>
             </value>
          </dict>
       </desc>
       <result>
          <array>
             <i>diego</i>
             <i>diego.da.silva.gomes@cern.ch</i>
             <i>Diego</i>
             <i>Da Silva Gomes</i>
             <i>/DC=org/DC=doegrids/OU=People/CN=Diego da Silva Gomes 849253</i>
             <i>+41 76 602 0801</i>
             <i>+41 22 76 76093</i>
             <i>gtalk:geneguvo@gmail.com</i>
          </array>
          ...
          <array>
             <i>pkreuzer</i>
             <i>Peter.Kreuzer@cern.ch</i>
             <i>Peter</i>
             <i>Kreuzer</i>
             <i>/DC=ch/DC=cern/OU=Organic Units/OU=Users/CN=pkreuzer/CN=406463/CN=Peter Kreuzer</i>
             <i/>
             <i/>
             <i/>
          </array>
          ...
       </result>
    </sitedb>

 ``username`` - CERN account or a pseudo-account for services.

 ``email`` - Person email.

 ``name`` - Person forename.

 ``surname`` - Person surname.

 ``dn`` - X509 certificate distinguished name.

 ``phone1`` - Primary phone number. Might be empty.

 ``phone2`` - Secondary phone numbe. Might be empty.

 ``im_handle`` - instant messaging  handle. Might be empty.

5. sites
~~~~~~~~

 Retrieve sites registered in SiteDB. The results aren't ordered in any particular way. 

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/sites>`_

 Curl example: ::
   
   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/sites"
   {"desc": {"columns": ["site_name", "tier_level", "tier", "country", "usage", "url", "logo_url", "devel_release", "manual_install"]}, "result": [
   ["FNALLPC", 3, "Tier 3", "Batavia, IL, USA", "OSG", "http://www.uscms.org/", "http://www.fnal.gov/faw/designstandards/filesfordownload/mark_blue.gif", null, null]
   ,["JINR-T1DISK", 1, "Tier 1", "Dubna, Russia", "LCG", null, null, "n", "n"]
   ,["Hephy-Vienna", 2, "Tier 2", "Austria", "LCG", "http://wwwhephy.oeaw.ac.at", "http://wwwhephy.oeaw.ac.at/hephy_logo.gif", "y", null]
   ,["KIPT", 2, "Tier 2", "Ukraine", null, null, null, null, null]
   ,["ITEP", 2, "Tier 2", "Russia", null, null, null, null, null]
   ,["INR", 2, "Tier 2", "Russia", null, null, null, null, null]
   ,["NCP-LCG2", 2, "Tier 2", "Islamabad/Pakistan", "LCG", null, null, null, null]
   ,["UKI-SCOTGRID-GLASGOW", 3, "Tier 3", "UK", null, null, null, null, null]
   ,["Brown-CMS", 3, "Tier 3", "Providence/US", "OSG", "http://brux2.hep.brown.edu/", null, null, "y"]
   ...
   ]}

 Browser output example: ::

   <sitedb>
      <desc>
         <dict>
            <key>columns</key>
            <value>
               <array>
                  <i>site_name</i>
                  <i>tier_level</i>
                  <i>tier</i>
                  <i>country</i>
                  <i>usage</i>
                  <i>url</i>
                  <i>logo_url</i>
                  <i>devel_release</i>
                  <i>manual_install</i>
               </array>
            </value>
         </dict>
      </desc>
      <result>
         <array>
            <i>FNALLPC</i>
            <i>3</i>
            <i>Tier 3</i>
             <i>Batavia, IL, USA</i>
             <i>OSG</i>
             <i>http://www.uscms.org/</i>
             <i>http://www.fnal.gov/faw/designstandards/filesfordownload/mark_blue.gif</i>
             <i></i>
             <i></i>
          </array>
          ...
          <array>
             <i>Bari</i>
             <i>2</i>
             <i>Tier 2</i>
             <i>Bari, Italy</i>
             <i>LCG</i>
             <i>http://webcms.ba.infn.it/cms-software</i>
             <i>None</i>
             <i>y</i>
             <i>y</i>
          </array>
          ...
      </result>
   </sitedb>

 ``site_name`` -  site name.
 
 ``tier_level`` - tier level.

 ``tier`` - tier label.

 ``country`` - country.

 ``usage`` - grid flavour.

 ``url`` - site web page.

 ``logo`` - logo image location.

 ``devel_release`` - currently unknown.

 ``manula_install`` - currently unknown.


6. site-names
~~~~~~~~~~~~~

 Retrieve site name associations. The results aren't ordered in any particular way.

 URL:  `<https://cmsweb.cern.ch/sitedb/data/prod/site-names>`_

 Curl example: ::

   $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/site-names"
   {"desc": {"columns": ["type", "site_name", "alias"]}, "result": [
   ["cms", "ASGC", "T1_TW_ASGC"]
   ,["cms", "BY-NCPHEP", "T3_BY_NCPHEP"]
   ,["cms", "Bari", "T2_IT_Bari"]
   ...
   ,["lcg", "ASGC", "Taiwan-LCG2"]
   ,["lcg", "BY-NCPHEP", "BY-NCPHEP"]
   ,["lcg", "Bari", "INFN-BARI"]
   ...
   ,["phedex", "ASGC", "T1_TW_ASGC_Buffer"]
   ,["phedex", "ASGC", "T1_TW_ASGC_MSS"]
   ,["phedex", "ASGC", "T1_TW_ASGC_Stage"]
   ]}

 Browser output example: ::
 
   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>type</i>
             <i>site_name</i>
             <i>alias</i> 
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>cms</i>
         <i>ASGC</i>
         <i>T1_TW_ASGC</i> 
       </array>
       <array>
         <i>cms</i>
         <i>BY-NCPHEP</i>
         <i>T3_BY_NCPHEP</i>
       </array>
       ...
       <array>
         <i>phedex</i>
         <i>cinvestav</i>
         <i>T3_MX_Cinvestav</i>
       </array>
     </result>
   </sitedb>

 ``type`` - alias type (One of : ``lcg``, ``cms``, ``phedex``).
  
 ``site_name`` - site name.
  
 ``alias`` - site name alias.


7. site-resources
~~~~~~~~~~~~~~~~~

 Retrieve sites CE`s and SE`s. The results aren't ordered in any particular way.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/site-resources>`_

 Curl example: ::
  
  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/site-resources"
  {"desc": {"columns": ["site_name", "type", "fqdn", "is_primary"]}, "result": [
  ["JHU", "SE", "hep.pha.jhu.edu", "n"]
  ,["JHU", "CE", "hep.pha.jhu.edu", "n"]
  ...
  ,["CC-IN2P3 AF", "SE", "ccsrmt2.in2p3.fr", "n"]
  ,["KNU", "CE", "cluster50.knu.ac.kr", "n"]
  ]}

 Browser output example: ::
  
  <sitedb>
    <desc>
      <dict>
        <key>columns</key>
        <value>
          <array>
            <i>site_name</i>
            <i>type</i>
            <i>fqdn</i>
            <i>is_primary</i>
          </array>
        </value>
      </dict>
    </desc>
    <result>
      <array>
        <i>JHU</i>
        <i>SE</i>
        <i>hep.pha.jhu.edu</i>
        <i>n</i>
      </array>
      <array>
        <i>JHU</i>
        <i>CE</i>
        <i>hep.pha.jhu.edu</i>
        <i>n</i>
      </array>
      ...
      <array>
        <i>CC-IN2P3 AF</i>
        <i>SE</i>
        <i>ccsrmt2.in2p3.fr</i>
        <i>n</i>
      </array>
    </result>
  </sitedb>  

  ``site_name`` - site name.

  ``type`` - One of SE or CE.

  ``fqdn`` - fully qualified host name.

  ``is_primary`` - y (yes) or n (no). If it is primary resource or not.

8. site-associations
~~~~~~~~~~~~~~~~~~~~

 Retrieve sites associations.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/site-associations>`_

 Curl example: ::
  
  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/site-associations"
  {"desc": {"columns": ["parent_site", "child_site"]}, "result": [
  ["ASGC", "UOS"]
  ,["ASGC", "Taiwan"]
  ,["ASGC", "TIFR"]
  ,["ASGC", "NZ-UOA"]
  ,["ASGC", "NTU_HEP"]
  ...
  ,["RAL", "ECDF"]
  ,["RAL", "Brunel"]
  ,["RAL", "Bristol"]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>parent_site</i>
             <i>child_site</i>
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>ASGC</i>
         <i>UOS</i>
       </array>
       <array>
         <i>ASGC</i>
         <i>Taiwan</i>
       </array>
       ...
       <array>
         <i>ASGC</i>
         <i>TIFR</i>
       </array>
       <array>
         <i>RAL</i>
         <i>Bristol</i>
       </array>
     </result>
   </sitedb>

 ``parrent_site`` - parent site name.

 ``child_site`` - child site name.


9. resource-pledges
~~~~~~~~~~~~~~~~~~~

 All pledges made are recorded in the database. Hence pledges cannot be updated or deleted as such, the site simply makes a new pledge for the same year to override the previous pledge. All pledges made are saved with the time stamp of the creation time; this is supplied automatically and is not given by the client, and is automatically returned on reads. 

 On read, all pledges made by the site are returned in increasing pledge date and year order. To obtain the current pledge for each year the client should keep just the last pledge for that year.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/resource-pledges>`_

 Curl example: ::

  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/test/resource-pledges"
  {"desc": {"columns": ["site_name", "pledge_date", "quarter", "cpu", "disk_store", "tape_store", "local_store"]}, "result": [
  ["ASGC", 1377787241.0, 2014, 0.0, 0.0, 0.0, null]
  ,["ASGC", 1377787241.0, 2013, 0.0, 0.0, 0.0, null]
  ,["ASGC", 1342100009.0, 2012, 2800.0, 1700.0, 2000.0, 660.0]
  ,["ASGC", 1309843279.0, 2011, 2025.0, 1350.0, 1125.0, 0.0]
  ,["ASGC", 1309843234.0, 2011, 2776.0, 950.0, 1600.0, 0.0]
  ,["ASGC", 1286197702.0, 2010, 2025.0, 1350.0, 1125.0, 0.0]
  ,["ASGC", 1280757755.0, 2010, 3290.0, 1080.0, 900.0, 0.0]
  ,["ASGC", 1273507301.0, 2010, 3000.0, 1080.0, 900.0, 0.0]
  ...
  ,["UCSD", 1276808631.0, 2010, 1500.0, 400.0, 0.0, 20.0]
  ,["UCSD", 1222697927.0, 2008, 1000.0, 200.0, 0.0, 20.0]
  ,["UCSD", 1189785292.0, 2007, 800.0, 20.0, 0.0, 20.0]
  ,["UCSD", 1181603897.0, 2007, 512.0, 48.0, 0.0, 0.0]
  ]}  

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>site_name</i>
             <i>pledge_date</i>
             <i>quarter</i>
             <i>cpu</i>
             <i>disk_store</i>
             <i>tape_store</i>
             <i>local_store</i>
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>ASGC</i>
         <i>1377787241</i>
         <i>2014</i>
         <i>0.0</i>
         <i>0.0</i>
         <i>0.0</i>
         <i></i>
       </array>
       <array>
         <i>ASGC</i>
         <i>1377787241</i>
         <i>2013</i>
         <i>0.0</i>
         <i>0.0</i>
         <i>0.0</i>
         <i></i>
       </array>
       ...
       <array>
         <i>cinvestav</i>
         <i>1371505604</i>
         <i>2013</i>
         <i>0.0</i>
         <i>10.0</i>
         <i>0.0</i>
         <i>10.0</i> 
       </array>
     </result>
   </sitedb>

 ``site_name`` - site name.

 ``pledge_date`` - date the pledge was created.

 ``quarter`` - pledge year.

 ``cpu`` - total cpu capacity, kHS06.

 ``disk_store`` - disk capacity, TB.

 ``tape_store`` - tape capacity, TB.

 ``local_store`` - local disk capacity, TB.

10. pinned-software
~~~~~~~~~~~~~~~~~~~

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/pinned-software>`_

 Currently not in use.  

11. site-responsibilities
~~~~~~~~~~~~~~~~~~~~~~~~~

 Retrieve sites responsibilities for all sites.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/site-responsibilities>`_

 Curl example: ::

  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/site-responsibilities"
  {"desc": {"columns": ["username", "site_name", "role"]}, "result": [
  ["pkreuzer", "CERN Tier-2 AI", "Site Executive"]
  ,["pkreuzer", "CERN Tier-2 HLT", "Site Executive"]
  ,["pkreuzer", "CERN Tier-2", "Site Executive"]
  ,["pkreuzer", "CERN Tier-0", "Site Executive"]
  ,["pkreuzer", "CERN", "Site Executive"]
  ,["pkreuzer", "CERN Tier-2 AI", "Site Admin"]
  ,["pkreuzer", "CERN Tier-2 HLT", "Site Admin"]
  ...
  ,["zielinsk", "FNALLPC", "Data Manager"]
  ,["barone", "Rome", "Data Manager"]
  ,["barone", "Rome", "Site Admin"]
  ,["bockjoo", "Florida", "Data Manager"]
  ]}

 Browser output example: ::
   
   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>username</i>
             <i>site_name</i>
             <i>role</i>
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>conway</i>
         <i>UCD</i>
         <i>Data Manager</i>
       </array>
       <array>
         <i>conway</i>
         <i>UCD</i>
         <i>Site Executive</i>
       </array>
       ...
       <array>
         <i>jtomasio</i>
         <i>NCG-INGRID-PT</i>
         <i>Site Admin</i>
       </array>
     </result>
   </sitedb>

 ``username`` - username.

 ``site_name`` - site name.

 ``role`` - role.

12. group-responsibilities
~~~~~~~~~~~~~~~~~~~~~~~~~~

 Retrieve group responsibilities.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/group-responsibilities>`_

 Curl example: ::

  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/group-responsibilities"
  {"desc": {"columns": ["username", "user_group", "role"]}, "result": [
  ["crovelli", "caf-alca", "Data Manager"]
  ,["demattia", "caf-alca", "Data Manager"]
  ,["pdmvserv@pdmvserv-test.cern.ch", "ReqMgr", "Admin"]
  ...
  ,["wmagent@cmssrv94.fnal.gov", "DataOps", "Production Operator"]
  ,["wmagent@cmssrv113.fnal.gov", "DBS", "Operator"]
  ,["wmagent@cmssrv113.fnal.gov", "DataOps", "T0 Operator"]
  ,["wmagent@cmssrv113.fnal.gov", "DataOps", "Production Operator"]
  ,["pilot@cmssrv161.fnal.gov", "DataOps", "T0 Operator"]
  ,["pilot@cmssrv161.fnal.gov", "DataOps", "Production Operator"]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>username</i>
             <i>user_group</i>
             <i>role</i>
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>crovelli</i>
         <i>caf-alca</i>
         <i>Data Manager</i>
       </array>
       <array>
         <i>demattia</i>
         <i>caf-alca</i>
         <i>Data Manager</i>
       </array>
       ...
       <array>
         <i>pdmvserv@pdmvserv-test.cern.ch</i>
         <i>ReqMgr</i>
         <i>Admin</i>
       </array>
     </result>
   </sitedb>

 ``username`` - username.

 ``user_group`` - group name.

 ``role`` -  role.

13. federations
~~~~~~~~~~~~~~~

 Retrieve cms federations. All data is up to date as is in REBUS. REBUS link : `<http://gstat-wlcg.cern.ch/apps/pledges/resources/>`_

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/federations>`_

 Curl example: ::

  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/federations"
  {"desc": {"columns": ["id", "name", "site_count", "country"]}, "result": [
  [31, "Austrian Tier-2 Federation", 1, "Austria"]
  ,[22, "Belgian Tier-2 Federation", 2, "Belgium"]
  ,[40, "SPRACE, Sao Paulo", 1, "Brazil"]
  ,[5, "IHEP, Beijing", 1, "China"]
  ,[15, "NICPB, Tallinn", 1, "Estonia"]
  ,[23, "NDGF/HIP Tier2", 1, "Finland"]
  ,[36, "CC-IN2P3 AF", 1, "France"]
  ,[42, "FR-CCIN2P3", 1, "France"]
  ...
  ,[11, "UC San Diego CMS T2", 1, "USA"]
  ,[4, "US-FNAL-CMS", 1, "USA"]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>id</i>
             <i>name</i>
             <i>site_count</i>
             <i>country</i>
           </array>
         </value>
       </dict>
     </desc>
    <result>
      <array>
        <i>31</i>
        <i>Austrian Tier-2 Federation</i>
        <i>1</i>
        <i>Austria</i>
      </array>
      <array>
        <i>22</i>
        <i>Belgian Tier-2 Federation</i>
        <i>2</i>
        <i>Belgium</i>
      </array>
      ...
      <array>
        <i>40</i>
        <i>SPRACE, Sao Paulo</i>
        <i>1</i>
        <i>Brazil</i>
      </array>
    </result>
  </sitedb>

 ``id`` - row id.

 ``name`` - federation name.
 
 ``site_count`` - gives information how many sites assigned to federation.

 ``country`` - country of given federation.

14. federations-sites
~~~~~~~~~~~~~~~~~~~~~

 Retrieve cms federations sites. All data is up to date as is in REBUS topology. REBUS topology link : `<http://gstat-wlcg.cern.ch/apps/topology/>`_ 
 Global admin can assign other sites to federation, which are not associated in REBUS. This information would be available only in SiteDB. 

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/federations-sites>`_

 Curl example: ::
 
  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/federations-sites"
  {"desc": {"columns": ["type", "site_id", "site_name", "alias", "fed_id", "site_count"]}, "result": [
  ["cms", 40, "CERN Tier-0", "T0_CH_CERN", 6, 1]
  ,["cms", 20, "CERN", "T1_CH_CERN", null, 0]
  ,["cms", 2121, "KIT", "T1_DE_KIT", 2, 1]
  ,["cms", 35, "PIC", "T1_ES_PIC", 37, 1]
  ,["cms", 8, "CC-IN2P3", "T1_FR_CCIN2P3", 42, 1]
  ,["cms", 32, "CNAF", "T1_IT_CNAF", 26, 1]
  ,["cms", 2662, "JINR-T1", "T1_RU_JINR", null, 0]
  ,["cms", 2682, "JINR-T1DISK", "T1_RU_JINR_Disk", null, 0]
  ,["cms", 19, "ASGC", "T1_TW_ASGC", 20, 1]
  ,["cms", 17, "RAL", "T1_UK_RAL", 7, 2]
  ...
  ,["cms", 2181, "UVA", "T3_US_UVA", null, 0]
  ,["cms", 2481, "Vanderbilt_EC2", "T3_US_Vanderbilt_EC2", null, 0]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
         <value>
           <array>
             <i>type</i>
             <i>site_id</i>
             <i>site_name</i>
             <i>alias</i>
             <i>fed_id</i>
             <i>site_count</i>
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>cms</i>
         <i>40</i>
         <i>CERN Tier-0</i>
         <i>T0_CH_CERN</i>
         <i>6</i>
         <i>1</i>
       </array>
       <array>
         <i>cms</i>
         <i>20</i>
         <i>CERN</i>
         <i>T1_CH_CERN</i>
         <i></i>
         <i>0</i>
       </array>
       ...
       <array>
         <i>cms</i>
         <i>2121</i>
         <i>KIT</i>
         <i>T1_DE_KIT</i>
         <i>2</i>
         <i>1</i>
       </array>
     </result>
   </sitedb>

 ``type`` - always cms.

 ``site_id`` - site id.
            
 ``site_name`` - site name.
             
 ``alias`` - site alias name.

 ``fed_id`` - federation row id.
           
 ``site_count`` - site counter in federation.

15. federations-pledges
~~~~~~~~~~~~~~~~~~~~~~~

 Retrieve federations pledges information. If pledge is changed, the new pledge is inserted in SiteDB with insertion timestamp. The newest one, is always current. All data is taken from REBUS, and no one is allowed to change it in SiteDB. All data are automatically fetched from REBUS Pledges - `<http://gstat-wlcg.cern.ch/apps/pledges/resources/>`_.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/federations-pledges>`_

 Curl example: ::
 
  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/test/federations-pledges"
  {"desc": {"columns": ["name", "country", "year", "cpu", "disk", "tape", "feddate"]}, "result": [
  ["Austrian Tier-2 Federation", "Austria", 2009, 3924.0, 268.0, 0.0, 1377962358.0]
  ,["Austrian Tier-2 Federation", "Austria", 2010, 7000.0, 500.0, 0.0, 1377962358.0]
  ,["Austrian Tier-2 Federation", "Austria", 2011, 3200.0, 300.0, 0.0, 1377962358.0]
  ,["Austrian Tier-2 Federation", "Austria", 2012, 3200.0, 300.0, 0.0, 1377962358.0]
  ,["Austrian Tier-2 Federation", "Austria", 2013, 3200.0, 500.0, 0.0, 1377962358.0]
  ,["Austrian Tier-2 Federation", "Austria", 2014, 3200.0, 300.0, 0.0, 1377962358.0]
  ,["Belgian Tier-2 Federation", "Belgium", 2009, 5600.0, 400.0, 0.0, 1377962358.0]
  ,["Belgian Tier-2 Federation", "Belgium", 2010, 9000.0, 670.0, 0.0, 1377962358.0]
  ,["Belgian Tier-2 Federation", "Belgium", 2011, 9600.0, 1190.0, 0.0, 1377962358.0]
  ,["Belgian Tier-2 Federation", "Belgium", 2012, 9600.0, 1560.0, 0.0, 1377962358.0]
  ,["Belgian Tier-2 Federation", "Belgium", 2013, 12000.0, 1850.0, 0.0, 1377962358.0]
  ...
  ,["Ukrainian Tier-2 Federation", "Ukraine", 2012, 4000.0, 300.0, 0.0, 1377962358.0]
  ,["Ukrainian Tier-2 Federation", "Ukraine", 2013, 6000.0, 350.0, 0.0, 1377962358.0]
  ,["Ukrainian Tier-2 Federation", "Ukraine", 2014, 9000.0, 650.0, 0.0, 1377962358.0]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
       <key>columns</key>
         <value>
           <array>
             <i>name</i>
             <i>country</i>
             <i>year</i>
             <i>cpu</i>
             <i>disk</i>
             <i>tape</i>
             <i>feddate</i> 
           </array>
         </value>
       </dict>
     </desc>
     <result>
       <array>
         <i>Austrian Tier-2 Federation</i>
         <i>Austria</i>
         <i>2009</i>
         <i>3924.0</i>
         <i>268.0</i>
         <i>0.0</i>
         <i>1377962358.0</i>
       </array>
       <array>
         <i>Austrian Tier-2 Federation</i>
         <i>Austria</i>
         <i>2010</i>
         <i>7000.0</i>
         <i>500.0</i>
         <i>0.0</i>
         <i>1377962358.0</i>
       </array>
       <array>
         <i>Austrian Tier-2 Federation</i>
         <i>Austria</i>
         <i>2011</i>
         <i>3200.0</i>
         <i>300.0</i>
         <i>0.0</i>
         <i>1377962358.0</i>
       </array>
     </result>
   </sitedb>

 ``name`` - federation name.
         
 ``country`` - federation country.
            
 ``year`` - federation pledge of year.

 ``cpu`` - CPU, TB.
        
 ``disk`` - Disk, TB.
         
 ``tape`` - Tape, TB. 
         
 ``feddate`` - Fetch date.

16. esp-credit
~~~~~~~~~~~~~~

 ESP Credits information. These fields are updated by Global Admin. Once inserted, it can`t be deleted. If ESP Credit value already exists, it will be rewritten.

 URL: `<https://cmsweb.cern.ch/sitedb/data/prod/esp-credit>`_

 Curl example: ::

  $curl -ks --cert $X509_USER_PROXY --key $X509_USER_PROXY "https://cmsweb.cern.ch/sitedb/data/prod/esp-credit"
  {"desc": {"columns": ["id", "site", "year", "esp_credit"]}, "result": [
  [1, 40, 2009, 17]
  ,[2, 2121, 2010, 17]
  ]}

 Browser output example: ::

   <sitedb>
     <desc>
       <dict>
         <key>columns</key>
           <value>
             <array>
               <i>id</i>
               <i>site</i>
               <i>year</i>
               <i>esp_credit</i>
             </array>
           </value>
         </dict>
       </desc>
       <result>
         <array>
           <i>1</i>
           <i>T0_CH_CERN</i>
           <i>2011</i>
           <i>17.0</i>
         </array>
         <array>
           <i>2</i>
           <i>T0_CH_CERN</i>
           <i>2012</i>
           <i>17.0</i>
         </array>
         ...
         <array>
           <i>3</i>
           <i>T1_CH_CERN</i>
           <i>2012</i>
           <i>4.5</i>
         </array>
       </result>
     </sitedb>

 ``id`` - row id. 
       
 ``site`` - site name alias.
         
 ``year`` - year of ESP Credit.
         
 ``esp_credit`` - ESP Credit value.

