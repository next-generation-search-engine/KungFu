import tensorflow as tf
from kungfu._utils import map_maybe

from ._tf_oplib import _op_lib
from .topology import peer_info


def _begin_nccl_ops(*args, **kwargs):
    if hasattr(_op_lib, 'kungfu_begin_nccl_ops'):
        return _op_lib.kungfu_begin_nccl_ops(*args, **kwargs)
    else:
        raise RuntimeError(
            "KungFu is not installed with NCCL. Please reinstall with KUNGFU_ENABLE_NCCL=1"
        )


def _scheduled_nccl_all_reduce_v2(t, op_name=None):
    if op_name is None:
        op_name = t.name
    return _op_lib.kungfu_scheduled_nccl_all_reduce_v2(t, op_name=op_name)


def group_nccl_all_reduce_v2(ts):
    names = [t.name for t in ts if t is not None]
    names = list(sorted(names))
    with tf.control_dependencies([
            _begin_nccl_ops(names, scope='global'),
    ]):
        return map_maybe(_scheduled_nccl_all_reduce_v2, ts)


def _scheduled_hierarchical_nccl_all_reduce_v2(t, op_names):
    return _op_lib.kungfu_scheduled_hierarchical_nccl_all_reduce_v2(
        t, op_names=op_names)


def group_hierarchical_nccl_all_reduce_v2(ts):
    names = [t.name for t in ts if t is not None]

    def reduce_op_name(name):
        return 'reduce_' + name

    def bcast_op_name(name):
        return 'bcast_' + name

    reduce_names = map_maybe(lambda t: reduce_op_name(t.name), ts)
    bcast_names = map_maybe(lambda t: bcast_op_name(t.name), ts)

    def all_reduce(args):
        i, t = args
        return _scheduled_hierarchical_nccl_all_reduce_v2(
            t, op_names=[reduce_names[i], bcast_names[i]])

    t_names = list(sorted(names))
    all_op_names = list([reduce_op_name(name) for name in t_names] +
                        [bcast_op_name(name) for name in t_names])

    with tf.control_dependencies([
            _begin_nccl_ops(all_op_names, scope='local'),
    ]):
        return map_maybe(all_reduce, enumerate(ts))
