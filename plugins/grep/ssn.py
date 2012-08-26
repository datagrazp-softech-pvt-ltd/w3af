'''
ssn.py

Copyright 2008 Andres Riancho

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

import re
import itertools

from core.controllers.plugins.grep_plugin import GrepPlugin
from core.data.bloomfilter.bloomfilter import scalable_bloomfilter

import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.constants.severity as severity
from .ssndata.ssnAreasGroups import areas_groups_map


class ssn(GrepPlugin):
    '''
    This plugin detects the occurence of US Social Security numbers in web pages.

    @author: dliz <dliz !at! users.sourceforge.net>
    '''
    # match numbers of the form: 'nnn-nn-nnnn' with some extra restrictions
    regex = '(?:^|[^\d-])(?!(000|666))([0-6]\d{2}|7([0-6]\d|7[012])) ?-? ?(?!00)(\d{2}) ?-? ?(?!0000)(\d{4})(?:^|[^\d-])'
    ssn_regex = re.compile(regex)
    

    def __init__(self):
        GrepPlugin.__init__(self)
        
        self._already_inspected = scalable_bloomfilter()
                
    def grep(self, request, response):
        '''
        Plugin entry point, find the SSN numbers.
        
        @parameter request: The HTTP request object.
        @parameter response: The HTTP response object
        @return: None.
        '''
        uri = response.getURI()
        
        if response.is_text_or_html() and response.getCode() == 200 \
        and response.getClearTextBody() is not None \
        and uri not in self._already_inspected:
            
            # Don't repeat URLs
            self._already_inspected.add(uri)
            
            found_ssn, validated_ssn = self._find_SSN(response.getClearTextBody())
            if validated_ssn:
                v = vuln.vuln()
                v.setPluginName(self.getName())
                v.setURI( uri )
                v.setId( response.id )
                v.setSeverity(severity.LOW)
                v.setName( 'US Social Security Number disclosure' )
                msg = 'The URL: "' + uri + '" possibly discloses a US '
                msg += 'Social Security Number: "'+ validated_ssn +'"'
                v.setDesc( msg )
                v.addToHighlight( found_ssn )
                kb.kb.append( self, 'ssn', v )
     
    def _find_SSN(self, body_without_tags):
        '''
        @return: SSN as found in the text and SSN in its regular format if the
                 body had an SSN
        '''
        validated_ssn = None
        ssn = None
        for match in self.ssn_regex.finditer(body_without_tags):
            validated_ssn = self._validate_SSN(match)
            if validated_ssn:
                ssn = match.group(0)
                ssn = ssn.strip()
                break

        return ssn, validated_ssn
    
    
    def _validate_SSN(self, potential_ssn):
        '''
        This method is called to validate the digits of the 9-digit number
        found, to confirm that it is a valid SSN. All the publicly available SSN
        checks are performed. The number is an SSN if: 
        1. the first three digits <= 772
        2. the number does not have all zeros in any digit group 3+2+4 i.e. 000-xx-####,
        ###-00-#### or ###-xx-0000 are not allowed
        3. the number does not start from 666-xx-####. 666 for area code is not allowed
        4. the number is not between 987-65-4320 to 987-65-4329. These are reserved for advts
        5. the number is not equal to 078-05-1120

        Source of information: wikipedia and socialsecurity.gov
        '''
        try:
            area_number = int(potential_ssn.group(2))
            group_number = int(potential_ssn.group(4))
            serial_number = int(potential_ssn.group(5))
        except:
            return False

        if not group_number:
            return False
        if not serial_number:
            return False

        group = areas_groups_map.get(area_number)        
        if not group:
            return False
        
        odd_one = xrange(1, 11, 2)
        even_two = xrange(10, 100, 2) # (10-98 even only)
        even_three = xrange(2, 10, 2)
        odd_four = xrange(11, 100, 2) # (11-99 odd only)
        le_group = lambda x: x <= group
        isSSN = False
    
        # For little odds (odds between 1 and 9)
        if group in odd_one:
            if group_number <= group:
                isSSN = True

        # For big evens (evens between 10 and 98)
        elif group in even_two:
            if group_number in itertools.chain(odd_one, 
                                               filter(le_group, even_two)):
                isSSN = True

        # For little evens (evens between 2 and 8)
        elif group in even_three:
            if group_number in itertools.chain(odd_one, even_two,
                                               filter(le_group, even_three)):
                isSSN = True

        # For big odds (odds between 11 and 99)
        elif group in odd_four:
            if group_number in itertools.chain(odd_one, even_two, even_three,
                                               filter(le_group, odd_four)):
                isSSN = True
        
        if isSSN:
            return '%s-%s-%s' % (area_number, group_number, serial_number)
        
        return None

    def end(self):
        '''
        This method is called when the plugin won't be used anymore.
        '''
        # Print results
        self.print_uniq( kb.kb.getData( 'ssn', 'ssn' ), 'URL' )

    def get_long_desc(self):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugins scans every response page to find the strings that are likely
        to be the US social security numbers. 
        '''
