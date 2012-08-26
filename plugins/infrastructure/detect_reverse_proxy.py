'''
detect_reverse_proxy.py

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

import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.option_list import OptionList

from core.controllers.plugins.infrastructure_plugin import InfrastructurePlugin
from core.controllers.w3afException import w3afException, w3afRunOnce

import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info

import re


class detect_reverse_proxy(InfrastructurePlugin):
    '''
    Find out if the remote web server has a reverse proxy.
    @author: Andres Riancho (andres.riancho@gmail.com)
    '''
    
    def __init__(self):
        InfrastructurePlugin.__init__(self)
        
        # Some internal variables
        self._run = True
        self._proxy_header_list = ['Via', 'Reverse-Via', 'X-Forwarded-For', 'Proxy-Connection', 
                                                'Max-Forwards', 'X-Forwarded-Host', 'X-Forwarded-Server']
        
    def discover(self, fuzzable_request ):
        '''
        @parameter fuzzable_request: A fuzzable_request instance that contains
                                                    (among other things) the URL to test.
        '''
        if not self._run:
            # This will remove the plugin from the infrastructure plugins to be run.
            raise w3afRunOnce()
        else:
            # I will only run this one time. All calls to detect_reverse_proxy return the same url's
            self._run = False
            
            # detect using GET
            if not kb.kb.getData( 'detect_transparent_proxy', 'detect_transparent_proxy'):            
                response = self._uri_opener.GET( fuzzable_request.getURL(), cache=True )
                if self._has_proxy_headers( response ):
                    self._report_finding( response )
           
            # detect using TRACE
            # only if I wasn't able to do it with GET
            if not kb.kb.getData( 'detect_reverse_proxy', 'detect_reverse_proxy' ):
                response = self._uri_opener.TRACE( fuzzable_request.getURL(), cache=True )
                if self._has_proxy_content( response ):
                    self._report_finding( response )
           
            # detect using TRACK
            # This is a rather special case that works with ISA server; example follows:
            # Request:
            # TRACK http://www.xyz.com.bo/ HTTP/1.1
            # ...
            # Response headers:
            # HTTP/1.1 200 OK
            # content-length: 99
            # ...
            # Response body:
            # TRACK / HTTP/1.1
            # Reverse-Via: MUTUN ------> find this!
            # ....
            if not kb.kb.getData( 'detect_reverse_proxy', 'detect_reverse_proxy' ):
                response = self._uri_opener.TRACK( fuzzable_request.getURL(), cache=True )
                if self._has_proxy_content( response ):
                    self._report_finding( response )
                
            # Report failure to detect reverse proxy
            if not kb.kb.getData( 'detect_reverse_proxy', 'detect_reverse_proxy' ):
                om.out.information( 'The remote web server doesn\'t seem to have a reverse proxy.' )

        
    def _report_finding( self, response ):
        '''
        Save the finding to the kb.
        
        @parameter response: The response that triggered the detection
        '''
        i = info.info()
        i.setPluginName(self.getName())
        i.setName('Reverse proxy')
        i.setId( response.getId() )
        i.setURL( response.getURL() )
        i.setDesc( 'The remote web server seems to have a reverse proxy installed.' )
        i.setName('Found reverse proxy')
        kb.kb.append( self, 'detect_reverse_proxy', i )
        om.out.information( i.getDesc() )
    
    def _has_proxy_headers( self, response ):
        '''
        Performs the analysis
        @return: True if the remote web server has a reverse proxy
        '''
        for proxy_header in self._proxy_header_list:
            for response_header in response.getHeaders():
                if proxy_header.upper() == response_header.upper():
                    return True
        return False
                    
    def _has_proxy_content( self, response ):
        '''
        Performs the analysis of the response of the TRACE and TRACK command.
        
        @parameter response: The HTTP response object to analyze
        @return: True if the remote web server has a reverse proxy
        '''
        response_body = response.getBody().upper()
        #remove duplicated spaces from body
        whitespace = re.compile('\s+')
        response_body = re.sub(whitespace, ' ', response_body)
        
        for proxy_header in self._proxy_header_list:
            # Create possible header matches
            possible_matches = [proxy_header.upper() + ':',  proxy_header.upper() + ' :']
            for possible_match in possible_matches:
                if possible_match in response_body:
                    return True
        return False

    def get_options( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = OptionList()
        return ol

    def set_options( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of get_options().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass
        
    def get_plugin_deps( self ):
        '''
        @return: A list with the names of the plugins that should be run before the
        current one.
        '''
        return ['infrastructure.detect_transparent_proxy']

    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin tries to determine if the remote end has a reverse proxy installed.
        
        The procedure used to detect reverse proxies is to send a request to the remote server and
        analyze the response headers, if a Via header is found, chances are that the remote site has
        a reverse proxy.
        '''
