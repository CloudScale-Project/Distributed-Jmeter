#
#  Copyright (c) 2015 XLAB d.o.o.
#  All rights reserved. This program and the accompanying materials
#  are made available under the terms of the Eclipse Public License v1.0
#  which accompanies this distribution, and is available at
#  http://www.eclipse.org/legal/epl-v10.html
#
class WebInteractions:

    def browsing_mix(self):
        operation = {}
        operation['/'] = 29
        operation['/best-sellers'] = 11
        operation['/new-products'] = 11
        operation['/product-detail'] = 21
        operation['/search?searchField=&keyword=&C_ID='] = 12
        operation['/search'] = 11
        operation['/shopping-cart'] =  2
        operation['/customer-registration'] = 0.82
        operation['/buy-confirm'] = 0.69
        operation['/buy'] = 0.75
        operation['/order-inquiry'] = 0.30
        operation['/order-display'] = 0.23
        operation['/admin-confirm'] = 0.09
        operation['/admin'] = 0.10
        operation['/payment'] = 0.69

        return operation

    def get_probability(self, operation):
        return self.browsing_mix().get(operation)

