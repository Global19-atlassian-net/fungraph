import itertools
from contextlib import suppress
from copy import deepcopy
from types import MappingProxyType
from typing import Callable, Any, Tuple, Dict, Optional, Union

import graphchain
import dask
from dask import delayed


def _context() -> dask.config.set:
    return dask.config.set(scheduler="sync",
                           delayed_optimize=graphchain.optimize)


class Node:

    def __init__(self, f: Callable[..., Any], *args: Any, **kwargs: Any):
        self._f = f
        self._args = list(args)
        self._kwargs = dict(kwargs)

    @property
    def args(self) -> Tuple[Any]:
        return tuple(self._args)

    @property
    def kwargs(self) -> MappingProxyType:
        return MappingProxyType(self._kwargs)

    @property
    def f(self) -> Callable[..., Any]:
        return self._f

    def __getitem__(self, item):
        return self.get(item)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def get(self, item: Union[str, int]) -> Any:
        try:
            return self._getarg(item)
        except (KeyError, IndexError):
            return self._getnamed(item, recursive=True)
        raise KeyError(f"{self} has no item {item}")

    def set(self, item: Union[str, int], value: Any) -> None:
        try:
            return self._setarg(item, value)
        except (KeyError, IndexError):
            return self._setnamed(item, value, recursive=True)
        raise KeyError(f"{self} has no item {item}")

    def _getarg(self, item: Union[str, int]):
        try:
            return self._args[item]
        except TypeError:
            try:
                return self._kwargs[item]
            except KeyError:
                raise KeyError(f"{self} has no argument {item}")

    def _setarg(self, key, value):
        try:
            self._args[key] = value
            return
        except TypeError:
            if key in self._kwargs:
                self._kwargs[key] = value
                return
        raise KeyError(f"{self} has no argument {key}")

    def _iterchildnodes(self):
        return ((k, n) for k, n in itertools.chain(enumerate(self.args), self.kwargs.items())
                if isinstance(n, Node)
                )

    def _getnamed(self, name: str, recursive: bool = True):
        for _, a in self._iterchildnodes():
            with suppress(Exception):
                if name == a.name:
                    return a
        if recursive:
            for _, a in self._iterchildnodes():
                with suppress(Exception):
                    return a.get(name, recursive=recursive)
        raise KeyError(f"{self} does not contain \"{name}\"")

    def _setnamed(self, name: str, value: Any, recursive: bool = True):
        found = False
        for index, a in self._iterchildnodes():
            with suppress(Exception):
                if name == a.name:
                    found = True
                    self[index] = value
        if recursive:
            for index, a in self._iterchildnodes():
                with suppress(Exception):
                    a.set(name, value, recursive=recursive)
                    found = True
        if not found:
            raise KeyError(f"{self} does not contain \"{name}\"")

    def todelayed(self) -> delayed:
        args = []
        for a in self.args:
            with suppress(AttributeError):
                a = a.todelayed()
            args.append(a)
        args = tuple(args)
        kwargs = {}
        for key, a in self.kwargs.items():
            with suppress(AttributeError):
                a = a.todelayed()
            kwargs[key] = a
        result = delayed(self.f)(*args, **kwargs)
        return result

    def __call__(self):
        return self.compute()

    def compute(self, cachedir: str = ".gracicache") -> Any:
        with _context():
            return self.todelayed().compute(location=cachedir)

    def __repr__(self):
        return f"AnonNode({self.f.__name__}, args={self.args}, kwargs={self.kwargs})"

    def clone(self):
        return deepcopy(self)

    def scan(self, arguments: Dict[str, Any], name: Optional[str] = None):
        result = []
        newargs = (zip(arguments.keys(), values) for values in zip(*(arguments.values())))
        for a in newargs:
            clone = self.clone()
            for k, v in a:
                clone.set(k, v)
            result.append(clone)
        if name:
            result = named(name, lambda *args: tuple(args), *result)
        else:
            result = node(lambda *args: tuple(args), *result)
        return result


class NamedNode(Node):
    def __init__(self, name: str, f: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__(f, *args, **kwargs)
        self.name = name

    def __repr__(self):
        return f"Node({self.name}, {self.f.__name__}, args={self.args}, kwargs={self.kwargs})"


def named(name: str, f: Callable[..., Any], *args: Any, **kwargs: Any) -> NamedNode:
    return NamedNode(name, f, *args, **kwargs)


def node(f: Callable[..., Any], *args: Any, **kwargs: Any) -> Node:
    return Node(f, *args, **kwargs)
