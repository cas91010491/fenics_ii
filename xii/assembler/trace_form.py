from ufl.corealg.traversal import traverse_unique_terminals
from xii.assembler.ufl_utils import *
import dolfin as df
import ufl


def trace_cell(o):
    '''
    UFL cell corresponding to restriction of o[cell] to its facets, performing
    this restriction on o[function-like], or objects in o[function space]
    '''
    # Space
    if hasattr(o, 'ufl_cell'):
        return trace_cell(o.ufl_cell())
    # Foo like
    if hasattr(o, 'ufl_element'):
        return trace_cell(o.ufl_element().cell())

    # Another cell
    cell_name = {'tetrahedron': 'triangle',
                 'triangle': 'interval'}[o.cellname()]
    
    return ufl.Cell(cell_name, o.geometric_dimension())


def trace_space(V, mesh):
    '''Construct a space where traces of V to mesh should live'''
    # Sanity
    assert mesh.ufl_cell() == trace_cell(V)

    elm = V.ufl_element()
    family = elm.family()
    degree = elm.degree()

    elm = type(elm)  # I.e. vector element stays verctor element
    # NOTE: Check out Witze Bonn's work on this and fill more
    family_map = {'Lagrange': 'Lagrange'}
    # This seems like a reasonable fall back option
    family = family_map.get(family, 'Discontinuous Lagrange')

    return df.FunctionSpace(mesh, elm(family, mesh.ufl_cell(), degree))


def Trace(v, mmesh, restriction='', normal=None):
    '''
    Annotate function for being a restriction onto manifold of codimension
    one
    '''
    # Prevent Trace(grad(u)). But it could be interesting to have this
    assert is_terminal(v)
    
    assert trace_cell(v) == mmesh.ufl_cell()
    # Not sure if it is really needed but will allow 5 types of traces
    assert restriction in ('',      # This makes sense for continuous foos
                           '+',     # For the remaining normal has to be
                           '-',     # present to get the orientation 
                           'jump',  # right
                           'avg')

    v.trace_ = {'type': restriction, 'mesh': mmesh, 'normal': normal}

    return v

# Consider now assembly of form, form is really a sum of integrals
# and here we want to assembly only the trace integrals. A trace integral
# is one where 
#
# 0) the measure is the trace measure
#
# 1) all the Arguments are associated with a cell whose trace_cell is
#    a cell of the measure
#
# 2) all the Arguments are associated either with a cell that matches
#    the cell of the measure (do not need restriction) and those whose
#    trace_cell is that of the measure
#
# NOTE these are suspects. What I will check in the assembler is that
# each arg above was created by Trace
def is_trace_integrand(expr, tdim):
    '''Some of the arguments need restriction'''
    return any(topological_dim(arg) > tdim and isinstance(arg, Argument)
               for arg in traverse_unique_terminals(expr))


def is_trace_integral(integral):
    '''Volume integral over an embedded cell'''
    return all((integral.integral_type() == 'cell',  # 0
                topological_dim(integral) < geometric_dim(integral),
                is_trace_integrand(integral.integrand(), topological_dim(integral))))


def trace_integrals(form):
    '''Extract trace integrals from the form'''
    return filter(is_trace_integral, form.integrals())
