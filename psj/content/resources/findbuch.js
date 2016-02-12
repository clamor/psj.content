var service = new SeeAlsoCollection();
        service.services = {
            'pndaks' : new SeeAlsoService('http://beacon.findbuch.de/seealso/pnd-aks/')
        };
        service.views = {
            'seealso-ul' : new SeeAlsoUL({
                                linkTarget: '_blank',maxItems: 100 })
        };
service.replaceTagsOnLoad();
