# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Author: Mathijs Dumon
# This work is licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. 
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/3.0/ or send
# a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.

from uuid import uuid1 as get_uuid

from weakref import WeakValueDictionary

from gtkmvc.support.metaclasses import ObservablePropertyMetaMT

def get_new_uuid():
    return unicode(get_uuid().hex)

def get_unique_list(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

class PyXRDMeta(ObservablePropertyMetaMT):

    ref_info_name = "%s_ref_info"

    def __init__(cls, name, bases, d):
        #get the model intel for this class type (excluding bases for now):        
        __model_intel__ = get_unique_list(d.get("__model_intel__", list()))

        #properties to be generated base on model intel named tuples:
        keys = [
            "__observables__", 
            "__storables__", 
            "__columns__",
            "__inheritables__",
            "__refinables__", 
            "__have_no_widget__"
        ]
    
        #Helper functions to to set or delete extra attributes on the class
        def set_attribute(name, value):
            d[name] = value
            setattr(cls, name, value)
        def del_attribute(name):
            del d[name]
            delattr(cls, name)
    
        #loop over the variables and fetch any custom values for this class (if present):
        for key in keys:
            d[key] = get_unique_list(d[key]) if key in d else list()
        
        #loop over the prop intels and add refinement info prop intels for
        #refinable scalars (floats and ints), their actual initialisation is
        #taken care of in the __call__ method of this metaclass
        ref_info_intels = list()
        for prop in __model_intel__:
            if prop.refinable and prop.data_type in (float, int):
                from properties import PropIntel
                ref_info_name = PyXRDMeta.ref_info_name % prop.name
                ref_info_intels.append(PropIntel(name=ref_info_name, data_type=object, storable=True))
                set_attribute(ref_info_name, None)
        __model_intel__.extend(ref_info_intels)
        
        #loop over the model intel and generate observables list:
        for prop in __model_intel__:
            if prop.observable: 
                d["__observables__"].append(prop.name)
            if hasattr(cls, prop.name):
                from properties import MultiProperty
                attr = getattr(cls, prop.name)
                if isinstance(attr, MultiProperty):
                        
                    pr_prop = "_%s" % prop.name
                    pr_optn = "_%ss" % prop.name
                    getter_name = "get_%s_value" % prop.name
                    setter_name = "set_%s_value" % prop.name
                
                    set_attribute(pr_prop, attr.value)
                    set_attribute(pr_optn, attr.options)
                    getter, setter = attr.create_accesors(pr_prop)
                    set_attribute(getter_name, getter)
                    set_attribute(setter_name, setter)
                    del_attribute(prop.name)                  
            
        # Add model intel from the base classes to generate the remaining 
        # properties, without overriding intels already present,
        # replace the variable by a set including the complete model intel for
        # all bases and including modifications arising in this metaclass:
        for base in bases: 
            base_intel = getattr(base, "__model_intel__", list())
            for prop in base_intel: 
                if not prop in __model_intel__:
                    __model_intel__.append(prop)
        setattr(cls, "__model_intel__", get_unique_list(__model_intel__))            
            
        #generate remaining properties based on model intel (including bases):
        for prop in __model_intel__:
            if prop.storable:   
                d["__storables__"].append(prop.name)
            if prop.is_column:
                # replace unicodes with strs for PyGtk
                data_type = prop.data_type if prop.data_type != unicode else str
                d["__columns__"].append((prop.name, data_type))
            if prop.inh_name:   d["__inheritables__"].append(prop.name)
            if prop.refinable:  d["__refinables__"].append(prop.name)
            if not prop.has_widget: d["__have_no_widget__"].append(prop.name)                
                
        #apply properties:
        for key in keys:
            setattr(cls, key, list(d[key]))

        return ObservablePropertyMetaMT.__init__(cls, name, bases, d)
                
    def __call__(cls, *args, **kwargs):
        #Check if uuid has been passed (e.g. when restored from disk)
        # if not generate a new one and set it on the instance
        uuid = kwargs.get("uuid", None)
        if uuid!=None: 
            del kwargs["uuid"]
        else:
            uuid = get_new_uuid()
        
        ref_infos = dict()
        for prop_intel in cls.__model_intel__:
            if prop_intel.refinable and prop_intel.data_type in (float, int):
                from generic.models import RefinementInfo
                ref_info_name = PyXRDMeta.ref_info_name % prop_intel.name
                
                info_args = kwargs.pop(ref_info_name, None)
                if info_args:
                    info = RefinementInfo.from_json(*info_args)
                else:
                    info = RefinementInfo(minimum = prop_intel.minimum, maximum = prop_intel.maximum)
                ref_infos[ref_info_name] = info
        
        #Create instance & set the uuid:
        instance = ObservablePropertyMetaMT.__call__(cls, *args, **kwargs)
        instance.__uuid__ = uuid
        
        #Add a reference to the instance for each model intel, 
        # so function calls (e.g. labels) work as expected,
        # and set the ref info attributes
        for prop_intel in instance.__model_intel__:
            prop_intel.container = instance           
        for ref_info_name, info in ref_infos.iteritems():
            setattr(instance, ref_info_name, info)

        #Add object to the object pool so other objects can 
        # retrieve it when restored from disk:
        pyxrd_object_pool.add_object(instance)
        return instance
        
class ObjectPool(object):
    
    def __init__(self, *args, **kwargs):
        object.__init__(self)
        self._objects = WeakValueDictionary()
        self.__stored_dicts__ = list()
    
    def add_object(self, obj, force=False, silent=True):
        if not obj.uuid in self._objects or force:
            self._objects[obj.uuid] = obj
        elif not silent:
            raise KeyError, "UUID %s is already taken by another object %s, cannot add object %s" % (obj.uuid, self._objects[obj.uuid], obj)
    
    def stack_uuids(self):
        #first get all values & uuids:
        items = self._objects.items()
        for key, value in items:
            value.stack_uuid()
            
    def restore_uuids(self):
        #first get all values & uuids:
        items = self._objects.items()
        for key, value in items:
            value.restore_uuid()
    
    def remove_object(self, obj):
        if obj.uuid in self._objects and self._objects[obj.uuid]==obj:
            del self._objects[obj.uuid]
    
    def get_object(self, uuid):
        return self._objects.get(uuid, None)
        
    def clear(self):
        self._objects.clear()
    
pyxrd_object_pool = ObjectPool()