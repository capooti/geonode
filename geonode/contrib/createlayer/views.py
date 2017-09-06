# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.shortcuts import redirect

from .forms import NewLayerForm
from .utils import create_layer


@login_required
def layer_create(request, template='createlayer/layer_create.html'):
    """
    Create an empty layer.
    """
    if request.method == 'POST':
        form = NewLayerForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            name = slugify(name.replace(".", "_"))
            title = form.cleaned_data['title']
            geometry_type = form.cleaned_data['geometry_type']
            permissions = form.cleaned_data["permissions"]
            layer = create_layer(name, title, request.user.username, geometry_type)
            layer.set_permissions(json.loads(permissions))
            return redirect(layer)
    else:
        form = NewLayerForm()

    ctx = {
        'form': form,
        'is_layer': True,
    }

    return render_to_response(template, RequestContext(request, ctx))
