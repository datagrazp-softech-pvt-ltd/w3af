'''
wsdl_greper.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info

from core.controllers.plugins.grep_plugin import GrepPlugin
from core.data.bloomfilter.bloomfilter import scalable_bloomfilter
from core.data.esmre.multi_in import multi_in


class wsdl_greper(GrepPlugin):
    '''
    Grep every page for web service definition files.
    
    @author: Andres Riancho (andres.riancho@gmail.com)
    '''
    WSDL_STRINGS = ( 'xs:int', 'targetNamespace', 'soap:body',
                     '/s:sequence', 'wsdl:', 'soapAction=',
                     # This isn't WSDL... but well...
                     'xmlns="urn:uddi"','<p>Hi there, this is an AXIS service!</p>' )
    _multi_in = multi_in( WSDL_STRINGS )

    def __init__(self):
        GrepPlugin.__init__(self)

        self._already_inspected = scalable_bloomfilter()
        self._disco_strings = ['disco:discovery ']

    def grep(self, request, response):
        '''
        Plugin entry point.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None, all results are saved in the kb.
        '''
        uri = response.getURI()
        if response.getCode() == 200  and uri not in self._already_inspected:
            self._already_inspected.add(uri)
            
            match_list = self._multi_in.query(response.body)
            if len(match_list):
                i = info.info()
                i.setPluginName(self.getName())
                i.setName('WSDL file')
                i.setURL( response.getURL() )
                i.setId( response.id )
                i.addToHighlight( *match_list )
                msg = 'The URL: "' +  i.getURL() + '" is a Web Services '
                msg += 'Description Language page.'
                i.setDesc( msg )
                kb.kb.append( self , 'wsdl' , i )
            
            is_disco = False
            for disco_string in self._disco_strings:
                if disco_string in response:
                    is_disco = True
                    break
                
            if is_disco:
                i = info.info()
                i.setPluginName(self.getName())
                i.setURL( response.getURL() )
                msg = 'The URL: "' +  i.getURL() + '" is a DISCO file that contains'
                msg += ' references to WSDLs.'
                i.setDesc( msg )
                i.addToHighlight( disco_string )
                kb.kb.append( self , 'disco' , i )
            
    def get_plugin_deps( self ):
        '''
        @return: A list with the names of the plugins that should be run before the
        current one.
        '''
        return []
    
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.print_uniq( kb.kb.getData( 'wsdl_greper', 'wsdl' ), 'URL' )
        self.print_uniq( kb.kb.getData( 'wsdl_greper', 'disco' ), 'URL' )
        
    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every page for WSDL definitions.
        
        Not all wsdls are found appending "?WSDL" to the url like crawl.wsdl_finder
        plugin does, this grep plugin will find some wsdl's that arent found by the 
        crawl plugin.
        '''
