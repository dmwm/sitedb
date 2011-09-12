'''
Some crude test for REST calls for sites.
'''
import unittest
from WMCore.Services.Requests import JSONRequests, Requests


class RESTSites_t(unittest.TestCase):


    def setUp(self):
        self.goodurls = [('/sites/list/T2_UK_SGrid_Bristol/', {}),
                ('/sites/contacts/T2_UK_SGrid_Bristol/', {'role':'Data Manager'}),
                ('/sites/contacts/T2_UK_SGrid_Bristol/', {'role':['Data Manager',
                                                                  'Site Admin']}),
                ('/sites/resource_pledge/T2_UK/2009.1', {}),
                ('/sites/resource_element/T2_UK/', {}),
                ('/sites/resource_element/T2_UK/?type=SE', {}),
                ('/sites/links/T2_UK/', {}),
                ('/sites/associations/T1_TW_ASGC/T3', {}),
                ]
        self.badurls = [('/sites/resource_pledge/T2_UK/2009.0', {}),
                ('/sites/resource_pledge/T2_UK/2009.5', {}),
                ('/sites/resource_element/T2_UK/?type=Foo', {}),]


    def tearDown(self):
        pass

    def testGoodGetJSON(self):
        headers={"Accept": "application/json"}
        json = JSONRequests('localhost:8010')
        self.runReq(self.goodurls, json, 200)

    def testGoodGetDefault(self):
        req = Requests('localhost:8010')
        self.runReq(self.goodurls, req, 200)

    def testBaadGetJSON(self):
        headers={"Accept": "application/json"}
        json = JSONRequests('localhost:8010')
        self.runReq(self.badurls, json, 400)

    def testBaadGetDefault(self):
        req = Requests('localhost:8010')
        self.runReq(self.badurls, req, 400)

    def runReq(self, urls, req, code):
        #TODO: check keys returned are good
        for u in urls:
            u[0]
            result = req.get(u[0], data=u[1])
            assert result[1] == code, 'got %s instead of %s for %s: %s' % (
                                                                    result[1],
                                                                    code,
                                                                    u[0],
                                                                    result[0])
    def testPut(self):
        pass

    def testPost(self):
        pass

    def testDelete(self):
        pass


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testSiteGet']
    unittest.main()
