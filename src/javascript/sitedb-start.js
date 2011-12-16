YUI({ base: REST_SERVER_ROOT + "/static/yui",
      comboBase: REST_SERVER_ROOT + "/static/yui?",
      root: "", combine: true, filter: REST_DEBUG && "raw" })
.use("yui", "controller", "history", "node", "dump", "substitute", "escape",
     "event-resize", "event-valuechange", "node-event-delegate",
     "io-base", "io-form", "json-parse",
     function(Y){ new SiteDB(Y, [Start, Sites, Pledges, People, Admin], REST_DEBUG); });
