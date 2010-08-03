from PyYUI.YUIRegistry import YUIRegistry
from PyYUI.YUIRoot import YUIRoot
from PyYUI.JSFunction import JSFunction
from Cheetah.Template import Template
from cherrypy import expose
from WMCore.WebTools.Page import TemplatedPage

class SiteList(TemplatedPage):
    def __init__(self, config = {}):
        TemplatedPage.__init__(self, config)
        self.yuiregistry = YUIRegistry(config.yui)
        self.yuiroot = self.yuiregistry.register('YUIRoot')
        self.dialog()
    
    @expose
    def index(self):
        return self.templatepage('sitelist', page=self)
    
    def dialog(self):
        domevent = self.yuiregistry.register('util.Event')
        
        json = self.yuiregistry.register('lang.JSON', 'myjson') #Just to register it
        domevent.onDOMReady('''function( ) {
    loadsites("http://localhost:8080/search/sitelist/");
}''')
        
        modalpanel = self.yuiregistry.register('Widget.Panel', 'mymodalpanel')
        
        modalpanel['bd'].append('This is the modalpanel body content. I think it should get expanded to fit the text')
        modalpanel['ft'].append('This is the modalpanel footer content')
        modalpanel['hd'].append('modalpanel')
        
        modalpanel.modal(m=True)
        
        event = self.yuiregistry.register('util.Event')
        event.addListener("showmodal", "click", "show", modalpanel, True)
        event.addListener("hidemodal", "click", "hide", modalpanel, True)
        
        
        func = JSFunction(components = [modalpanel, event])
        
        domevent.onDOMReady(func)
        self.yuiroot.add(domevent)