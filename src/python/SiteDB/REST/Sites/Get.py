'''
Created on 22 Jul 2009

@author: metson
'''
from WMCore.WebTools.RESTModel import RESTModel
from WMCore.Services.Dashboard.Dashboard import Dashboard
from WMCore.Services.SAM.SAM import SAM
from SiteDB.REST.Validate import Validator

class Get(RESTModel):
    '''
    Get: Get data related to the sites known to SiteDB
     
    '''

    def __init__(self, config):
        '''
        Initialise the RESTModel and add some methods to it.
        '''
        RESTModel.__init__(self, config)
        
        del self.methods['POST']
        
        validator = Validator({'dbi':self.dbi})
        
        self.dashboard = Dashboard(dict = {
                  'endpoint': self.config.services.dashboard,
                  'cachepath': self.config.services.cachepath,
                  'logger': self})
        self.samtests = SAM(dict = {
                  'endpoint': self.config.services.sam,
                  'cachepath': self.config.services.cachepath,
                  'cert': config.services.hostcert,
                  'key': config.services.hostkey,
                  'logger': self})
        
        self.methods['GET'] = {'list':{'args':['name', 'scheme'],
                                        'call': self.list,
                                        'version': 2,
                                        'validation': [validator.validate_scheme, 
                                                       validator.validate_name]},
                              'status':{'args': ['name'],
                                        'call': self.status,
                                        'version': 2,
                                        'validation': [validator.validate_scheme, 
                                                       validator.validate_name]},
                              'software':{'args': ['name'],
                                        'call': self.software,
                                        'version': 2,
                                        'validation': [validator.validate_scheme, 
                                                       validator.validate_name]},
                              'resource_element':{'args':['name', 'type'],
                                        'call': self.resource_element,
                                        'version': 2,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_name,
                                                       validator.validate_resource_type]},
                              'resource_pledge':{'args':['name', 'quarter'],
                                        'call': self.resource_pledge,
                                        'version': 2,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_name,
                                                       validator.validate_quarter]},
                              'pledge_history':{'args':['name'],
                                        'call': self.pledge_history,
                                        'version': 1},
                              'contacts':{'args':['name', 'role'],
                                        'call': self.contacts,
                                        'version': 2,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_name,
                                                       validator.validate_role]},
                              'groups':{'args': ['name'],
                                        'call': self.groups,
                                        'version': 1},
                              'links':{'args': ['name'],
                                        'call': self.links,
                                        'version': 1,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_name]},
                              'associations':{'args': ['parent', 'child', 'scheme'],
                                        'call': self.associations,
                                        'version': 1,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_associations]},
                              'names':{'args':['name', 'scheme', 'limit'],
                                        'call': self.names,
                                        'version': 1,
                                        'validation': [validator.validate_scheme,
                                                       validator.validate_limit_scheme, 
                                                       validator.validate_name]}}
        
    def list(self, *args, **kwargs):
        """
        Return a list of sites matching name in the chosen format
        Args: name='T%', scheme='cms_name'
        """
        input = self.sanitise_input(args, kwargs, 'list')
        binds = []
        
        for n in self.makelist(input['name']): 
            binds.append({'name': n + '%'})
        sql = ""
        if input['scheme'] == 'resource':
            sql = """select * from siteinfo_v2 where id in (
                    select site from resource_element_v2 where fqdn like :name')"""
        elif input['scheme'] == 'lcg_name':
            # TODO: this needs a schema change and a refactor...
            sql = """select * from siteinfo_v2 where id in(select SITE_CMS_NAME_MAP.SITE_ID from SAM_NAME
  join SAM_CMS_NAME_MAP on SAM_CMS_NAME_MAP.SAM_ID = SAM_NAME.id
  join SITE_CMS_NAME_MAP on SITE_CMS_NAME_MAP.CMS_NAME_ID = SAM_CMS_NAME_MAP.CMS_NAME_ID
where SAM_NAME.NAME like :name)"""
        else:
            sql = "select * from siteinfo_v2 where %s like :name" % input['scheme']
            
        result = self.dbi.processData(sql, binds)
        data = self.formatDict(result)
        
        return {'binds': binds, 'sitelist':data}
         
    def status(self, *args, **kwargs):
        """
        return the status of a given site 
        Args: name
        """
        input = self.sanitise_input(args, kwargs, 'status')
        
        return self.dashboard.getStatus(name=input['name'])  
    
    def software(self, *args, **kwargs):
        """
        Return a list of software installed at the site as reported by SAM tests
        and it's pin status.
        
        Args: names
        
        TODO: add in pin status
        """
        input = self.sanitise_input(args, kwargs, 'software')
        celist = self.resource_element(name=input['name'], type='CE')
        sw = []
        pinsql = """select release, arch from pinned_releases 
        where ce_id = (select id from resource_element_v2 where fqdn = :ce)"""
        mansql = """select MANUALINSTALL from resource_element_v2 
        where fqdn = :ce and RESTYPE='CE'"""
        for ce in celist['resource_element']:
            result = self.dbi.processData(pinsql, {'ce': ce['fqdn']})
            pins = self.formatDict(result)
            sorted_pins = {}
            for pin in pins:
                if pin['arch'] in sorted_pins.keys():
                    sorted_pins[pin['arch']].append(pin['release'])
                else:
                    sorted_pins[pin['arch']] = [pin['release']]
            result = self.dbi.processData(mansql, {'ce': ce['fqdn']})
            manual = False
            if self.formatDict(result)[0]['manualinstall']:
                manual = True
            installed = self.samtests.getCMSSWInstalls(ce['fqdn'])
            sw.append({ce['fqdn']: {'installed': installed,
                                    'pinned': sorted_pins,
                                    'manual': manual}})
        return sw
    
    def resource_element(self, *args, **kwargs):
        """
        Return the names of a resource element of _type_ for _site_
        Args: name, type
        """
        input = self.sanitise_input(args, kwargs, 'resource_element')
        data = {}
        binds = []
        sql ="""select resource_element_v2.fqdn, 
                        resource_element_v2.restype,
                        siteinfo_v2.cms_name
                        from resource_element_v2
                        join siteinfo_v2 on siteinfo_v2.id = resource_element_v2.site
                    where siteinfo_v2.cms_name like :name 
                    and restype like :type"""
        for n in self.makelist(input['name']): 
            binds.append({'name': n + '%', 'type' : input['type']})
        result = self.dbi.processData(sql, binds)
        data['resource_element'] = self.formatDict(result)
        data['binds'] = binds
                
        return data
    
    def resource_pledge(self, *args, **kwargs):
        """
        Return the pledged resources available at _site_ during _quarter_
        Args: names, quarter
        """
        input = self.sanitise_input(args, kwargs, 'resource_pledge')
        sql = """select
    siteinfo_v2.cms_name, max(PLEDGEQUARTER) quarter_pledged,
    cpu, job_slots, disk_store, tape_store, wan_store, local_store, 
    national_bandwidth, opn_bandwidth
from resource_pledge
 join siteinfo_v2 on siteinfo_v2.id = RESOURCE_PLEDGE.site
where siteinfo_v2.cms_name like :site and PLEDGEQUARTER <= :quarter
and pledgedate in (
    select
        max(RESOURCE_PLEDGE.pledgedate)
        from RESOURCE_PLEDGE 
        join siteinfo_v2 on siteinfo_v2.id = RESOURCE_PLEDGE.site
    where siteinfo_v2.cms_name like :site and PLEDGEQUARTER <= :quarter

    group by cms_name
)
group by siteinfo_v2.cms_name, cpu, job_slots, disk_store, tape_store, wan_store, local_store, 
    national_bandwidth, opn_bandwidth

order by siteinfo_v2.cms_name, max(PLEDGEQUARTER) desc"""
        
        data = {}
        try:
            binds = []
            for n in self.makelist(input['name']): 
                    binds.append({'site': n + '%','quarter': input['quarter']})
            result = self.dbi.processData(sql, binds)
            data['resource_pledge'] = self.formatDict(result)
            
            def red_fun(x, y):
                d = {}
                d['job_slots'] = x.get('job_slots', 0) + y.get('job_slots', 0)
                d['local_store'] = x.get('local_store', 0) + y.get('local_store', 0)
                d['wan_store'] = x.get('wan_store', 0) + y.get('wan_store', 0)
                d['disk_store'] = x.get('disk_store', 0) + y.get('disk_store', 0)
                d['tape_store'] = x.get('tape_store', 0) + y.get('tape_store', 0)
                d['national_bandwidth'] = x.get('national_bandwidth', 0) + y.get('national_bandwidth', 0)
                d['opn_bandwidth'] = x.get('opn_bandwidth', 0) + y.get('opn_bandwidth', 0)
                d['cpu'] = x.get('cpu', 0) + y.get('cpu', 0)
                return d
            
            data['resource_totals'] = reduce(red_fun, data['resource_pledge'])
            data['binds'] = binds
        except Exception, e:
            self.exception("Could not get resource_pledge for input:" % input)
            data = {"exception": e, 
                    "message": "Could not get resource_pledge",
                    "execeptiontype": str(type(e)).split("'")[1],
                    'binds': binds}
        return data
    
    def pledge_history(self, *args, **kwargs):
        """
        Return the pledged resources available at site _name_ over time.
        Args: names 
        """
        input = self.sanitise_input(args, kwargs, 'pledge_history')
        return {}
    
    def contacts(self, *args, **kwargs):
        """
        Return the people associated to _name_, if specified with _role_
        Args: names, roles
        """
        input = self.sanitise_input(args, kwargs, 'contacts')
        data = binds = {}
        try:
            sql = """select siteinfo_v2.cms_name, 
contact.forename, contact.surname, contact.email, 
contact.phone1, contact.phone2, contact.im_handle, role.title
from site_responsibility
join contact on contact.id = site_responsibility.contact
join role on role.id = site_responsibility.role
join siteinfo_v2 on siteinfo_v2.id = site_responsibility.site
 where lower(role.title) like :role 
and role.id != 1
and siteinfo_v2.cms_name like :name
order by contact.surname"""
            binds = []
            for n in self.makelist(input['name']):
                for r in self.makelist(input['role']): 
                    binds.append({'name': n + '%', 'role' : r.lower()})
            result = self.dbi.processData(sql, binds)
            sorted_contacts = {}
            for contact in self.formatDict(result):
                eml = contact['email']
                if eml in sorted_contacts.keys():
                    sorted_contacts[eml]['role'].append(contact['title'])
                else:
                    sorted_contacts[eml] = contact
                    sorted_contacts[eml]['role'] = []
                    sorted_contacts[eml]['role'].append(contact.pop('title'))
            data['contacts'] = sorted_contacts.values()
            data['binds'] = binds
        except Exception, e:
            self.exception("Could not get contacts for input:" % input)
            data = {"exception": e, 
                    "message": "Could not get contacts",
                    "execeptiontype": str(type(e)).split("'")[1],
                    'binds': binds}
        return data
       
    def groups(self, *args, **kwargs):
        """
        Return the groups associated to _site_
        Args: names
        """
        input = self.sanitise_input(args, kwargs, 'groups')
        return {}
    
    def names(self, *args, **kwargs):
        """
        Return the name of _site_ for _scheme_. If no _site_ is specified return 
        all the sites name for _scheme_, allow for partial. Calling names with 
        no arguments will list all CMS names in SiteDB.
        
        Args: name (a CMS name), scheme (one of: cms_name, site_name, lcg_name)
        """
        input = self.sanitise_input(args, kwargs, 'names')
        # TODO: this needs a schema change and a refactor...
        sql = """select %s from SAM_NAME
  join SAM_CMS_NAME_MAP on SAM_CMS_NAME_MAP.SAM_ID = SAM_NAME.id
  join SITE_CMS_NAME_MAP on SITE_CMS_NAME_MAP.CMS_NAME_ID = SAM_CMS_NAME_MAP.CMS_NAME_ID
  join siteinfo_v2 on siteinfo_v2.ID = SITE_CMS_NAME_MAP.SITE_ID
  join resource_element_v2 on resource_element_v2.site = siteinfo_v2.ID
  %s
  order by siteinfo_v2.cms_name, sam_name.name, resource_element_v2.FQDN"""
        condition = ''
        limit = "siteinfo_v2.cms_name, siteinfo_v2.site_name, sam_name.name, resource_element_v2.FQDN"

        binds = {'name': input['name'] + '%'}
        
        if input['scheme'] == 'resource':
            condition = 'where resource_element_v2.FQDN like :name'
            binds['name'] = input['name']
        elif input['scheme'] == 'lcg_name':
            condition = 'where sam_name.name like :name'
        else:
            condition = 'where siteinfo_v2.%s like :name' % (input['scheme'])
            
        if input['limit'] == 'resource':
            limit = 'resource_element_v2.FQDN'
        elif input['limit'] == 'lcg_name':
            limit = 'sam_name.name'
        elif input['limit'] == 'site_name':
            limit = 'siteinfo_v2.site_name'
        elif input['limit'] == 'cms_name':
            limit = 'siteinfo_v2.cms_name'
                            
        sql = sql % (limit, condition)
        result = self.dbi.processData(sql, binds)
        data = {}
        data['names'] = self.formatDict(result)
        data['binds'] = binds
        data['limit'] = input['limit'] 
        return data
    
    def links(self, *args, **kwargs):
        """
        Return monitoring links for the site
        Args: name
        """
        input = self.sanitise_input(args, kwargs, 'links')
        data = binds = {}
        try:
            sql = """select siteinfo_v2.cms_name, sitelinks.url from sitelinks
join siteinfo_v2 on siteinfo_v2.id = sitelinks.SITEID
where siteinfo_v2.cms_name like :name"""
            binds = []
            for n in self.makelist(input['name']): 
                binds.append({'name': n + '%'})
            result = self.dbi.processData(sql, binds)
            data['links'] = self.formatDict(result)
            data['binds'] = binds
        except Exception, e:
            self.exception("Could not get links for input:" % input)
            data = {"exception": e, 
                    "message": "Could not get links",
                    "execeptiontype": str(type(e)).split("'")[1],
                    'binds': binds}
        return data
    
    def associations(self, *args, **kwargs):
        input = self.sanitise_input(args, kwargs, 'associations')
        data = {}
        sql = """select pi.CMS_NAME as Parent_Name, ci.CMS_NAME as Child_Name
from site_association sa, siteinfo_v2 pi, siteinfo_v2 ci
where sa.PARENT_SITE = pi.id
and sa.CHILD_SITE = ci.ID
and ci.%s like :child
and pi.%s like :parent""" % (input['scheme'], input['scheme']) 
        binds = []
        for p in self.makelist(input['parent']):
            for c in self.makelist(input['child']):
                binds.append({'parent': p + '%',
                              'child': c + '%'})
        result = self.dbi.processData(sql, binds)
        data['links'] = self.formatDict(result)
        data['binds'] = binds
        return data
    
    def formatOneDList(self, result):
        """
        Format a list of single elements into a list
        """
        out = []
        for r in result:
            for i in r.fetchall():
                assert len(i) == 1, 'formatOneDList can only format single element lists'
                out.append(i[0])
            r.close()        
        return out