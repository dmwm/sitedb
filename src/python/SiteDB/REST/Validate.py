'''
Validation functions for SiteDB queries
'''
from WMCore.DataStructs.WMObject import WMObject
from WMCore.Lexicon import cmsname
from datetime import date
import re

class Validator(WMObject):
    
    def validate_name(self, input):
        if 'name' not in input.keys():
            if input['scheme'] == 'cms_name':
                input['name'] ='T%'
            else:
                input['name'] = 'CERN'  
        if input['scheme'] == 'cms_name' and input['name'] !='%':
            for name in self.makelist(input['name']):
                cmsname(name)
        elif input['scheme'] == 'resource':
            reg = "(\/|\/([\w#!:.?+=&%@!\-\/]))?"
            assert re.compile(reg).match(input['name']) != None , \
              "'%s' is not a valid FQDN (regexp: %s)" % (input['name'], reg)
        return input
    
    def validate_scheme(self, input):
        if not 'scheme' in input.keys():
            input['scheme'] = 'cms_name'
        schemes = ['cms_name', 'site_name', 'resource', 'lcg_name']
        in_schemes =  self.makelist(input['scheme'])
        assert len(in_schemes) == 1, \
                "Only one scheme is allowed you have provided %s: %s" % \
                            (len(in_schemes), in_schemes)
        assert input['scheme'].lower() in schemes, \
                "Unsupported naming scheme (%s), please chose one of %s" % \
                            (input['scheme'], schemes)
        return input
    
    def validate_limit_scheme(self, input):
        "Check that the limiting scheme is valid or None"
        if not 'limit' in input.keys():
            input['limit'] = None
        else:
            self.validate_scheme({'scheme':input['limit']})
        return input
        
    def validate_role(self, input):
        if 'role' in input.keys():
            
            sql = """select lower(title) from ROLE where id 
                        in (select distinct ROLE from site_responsibility)"""
            result = self.config['dbi'].processData(sql)
            formatted_result = self.formatOneDList(result)
            
            for role in self.makelist(input['role']):
                assert role.lower() in formatted_result,\
                     '%s is not a known role' % role
        elif not 'role' in input.keys():
            input['role'] = '%'
        return input
    
    def validate_quarter(self, input):
        if not 'quarter' in input.keys():
            # Set a default
            now = date.today()
            year = now.year
            quarter = 0
            for i in xrange(0, 4, 1):
                if now.month in xrange ((3*i) + 1, 1 + (3*(1+i)), 1):
                    quarter = i + 1
            input['quarter'] = '%s.%s' % (year, quarter) 
        else:
            quarter = int(input['quarter'].split('.')[1])
            assert quarter>=1, 'invalid quarter, should be 1-4, not %s' % quarter
            assert quarter<=4, 'invalid quarter, should be 1-4, not %s' % quarter
        return input
    
    def validate_release(self, input):

        return input
    
    def validate_architecture(self, input):

        return input
    
    def validate_is_ce(self, input):
      
        return input
    
    def validate_resource_type(self, input):
        if not 'type' in input.keys():
            input['type'] = '%'
        else:
            if input['type'].upper() not in ['CE', 'SE' , 'SQUID', '%']:
                raise TypeError('%s is not a CE, SE or SQUID' % input['type'].upper())
        return input
    
    def validate_link(self, input):
        assert 'url' in input.keys()
        reg = "(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?"
        assert re.compile(reg).match(input['url']) != None , \
              "'%s' is not a valid URL (regexp: %s)" % (input['url'], reg)
        return input
    
    def validate_associations(self, input):
        if 'scheme' in input.keys():
            assert 'resource' != input['scheme'].lower(), "Resource is not a valid" +\
                    " scheme for the associations API, please use one" +\
                    " of cms_name or site_name"
        else:
            input['scheme'] = 'cms_name'
        if 'parent' in input.keys():
            self.validate_name({'name':input['parent'],
                                'scheme': input['scheme']})
        else:
            input['parent'] = 'T'
        if 'child' in input.keys():
            self.validate_name({'name':input['child'],
                                'scheme': input['scheme']})
        else:
            input['child'] = 'T'    
        return input
    
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