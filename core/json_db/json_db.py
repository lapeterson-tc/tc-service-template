"""JsonDB module for storing and loading entities from disk."""

# standard library
import gzip as gz
import importlib
import json
import os
import threading
import time
from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from enum import Enum
from functools import cached_property, lru_cache
from pathlib import Path
from types import GenericAlias
from typing import Any, ParamSpec, TypeVar, Union, cast

# third-party
import uuid6
from pydantic import BaseModel, Field
from pydantic.fields import Undefined
from pydantic.typing import NoArgAnyCallable

P = TypeVar('P', bound=BaseModel)

SortBy = Enum('SortBy', ['CREATED', 'MODIFIED', 'INDEX'])
SortOrder = Enum('SortOrder', {'ASC': 'asc', 'DESC': 'desc'})


def Embedded(  # noqa: N802
    default: Any = Undefined,
    *,
    default_factory: NoArgAnyCallable | None = None,
    alias: str | None = None,
    title: str | None = None,
    description: str | None = None,
    exclude: Union['AbstractSetIntStr', 'MappingIntStrAny', Any] | None = None,  # noqa: F821
    include: Union['AbstractSetIntStr', 'MappingIntStrAny', Any] | None = None,  # noqa: F821
    const: bool | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    allow_inf_nan: bool | None = None,
    max_digits: int | None = None,
    decimal_places: int | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    unique_items: bool | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    allow_mutation: bool = True,
    regex: str | None = None,
    discriminator: str | None = None,
    repr: bool = True,  # pylint: disable=redefined-builtin  # noqa: A002
    **extra: Any,
):
    """Mark a pydantic field as being embedded.

    An embedded field will not be written to its own file, but will be written to
    the file of the parent entity.
    """
    return Field(
        default=default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        json_db_embedded=True,
        **extra,
    )


def Index(  # noqa: N802
    default: Any = Undefined,
    *,
    default_factory: NoArgAnyCallable | None = lambda: str(uuid6.uuid7()),
    alias: str | None = None,
    title: str | None = None,
    description: str | None = None,
    exclude: Union['AbstractSetIntStr', 'MappingIntStrAny', Any] | None = None,  # noqa: F821
    include: Union['AbstractSetIntStr', 'MappingIntStrAny', Any] | None = None,  # noqa: F821
    const: bool | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    allow_inf_nan: bool | None = None,
    max_digits: int | None = None,
    decimal_places: int | None = None,
    min_items: int | None = None,
    max_items: int | None = None,
    unique_items: bool | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    allow_mutation: bool = True,
    regex: str | None = None,
    discriminator: str | None = None,
    repr: bool = True,  # pylint: disable=redefined-builtin  # noqa: A002
    **extra: Any,
):
    """Mark a pydantic field as being an index."""
    return Field(
        default=default,
        default_factory=default_factory,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        json_db_index=True,
        **extra,
    )


A = ParamSpec('A')
R = TypeVar('R')


def EnforceWritePolicies(fn: Callable[A, R]) -> Callable[A, R]:  # noqa: N802
    """Decorate function to enforce write policies."""

    def _decorator(*args: A.args, **kwargs: A.kwargs) -> R:
        self: 'JsonDB' = args[0]  # type: ignore  # noqa: UP037
        if not self.allow_multiprocess_write and self.pid != os.getpid():
            ex_msg = 'Multiprocess write is not allowed.'
            raise RuntimeError(ex_msg)
        if not self.allow_multithread_write and (
            self.tid != threading.get_ident() or self.pid != os.getpid()
        ):
            ex_msg = 'Multithread write is not allowed.'
            raise RuntimeError(ex_msg)
        return fn(*args, **kwargs)

    return _decorator


I = TypeVar('I')  # noqa: E741


class JsonDB:
    """JsonDB class for storing and loading entities from disk."""

    def __init__(
        self,
        path: str | Path,
        *,
        gzip: bool = True,
        json_args=None,
        allow_multiprocess_write=True,
        allow_multithread_write=True,
    ) -> None:
        """Initialize JsonDB."""
        self.allow_multiprocess_write = allow_multiprocess_write
        self.allow_multithread_write = allow_multithread_write
        self.gzip = gzip
        self.json_args = json_args if json_args is not None else {}
        self.path = Path(path)
        if self.path.exists() and not self.path.is_dir():
            ex_msg = 'Path is not a directory.'
            raise ValueError(ex_msg)
        self.path.mkdir(parents=True, exist_ok=True)
        self.pid = os.getpid()
        self.tid = threading.get_ident()

        self._cleanup()
        self._migrate_gzip()

    @contextmanager
    def acquire(
        self, cls: type[P], index_value: Any, *, timeout: float = 20
    ) -> Generator[P, None, None]:
        """Aquire entity of a given class by index value."""
        try:
            now = time.time_ns()
            directory = self._storage_directory(cls)
            lock_file_path = directory / f'{index_value}#{now}.lock'
            lock_file_path.touch()

            lock_files = directory.glob(f'{index_value}#*.lock')
            winner = self._get_winning_lock_file(lock_files)

            while winner != lock_file_path and (timeout == -1 or timeout > 0):
                time.sleep(0.5)
                if timeout != -1:
                    timeout -= 0.5
                lock_files = directory.glob(f'{index_value}#*.lock')
                winner = self._get_winning_lock_file(lock_files)

            if winner != lock_file_path:
                ex_msg = 'Entity has already been aquired.'
                raise RuntimeError(ex_msg)

            yield self.load(cls, index_value)
        except Exception as ex:
            ex_msg = 'Could not acquire entity.'
            raise RuntimeError(ex_msg) from ex
        finally:
            lock_file_path.unlink()

    def get_paths(
        self,
        cls: type[P],
        *,
        sort_by: SortBy | str = SortBy.INDEX,
        sort_order: SortOrder | str = SortOrder.ASC,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Path]:
        """Get all paths for entities of the given type"""

        if isinstance(sort_by, str):
            sort_by = SortBy[sort_by.upper()]
        # pylint: disable=isinstance-second-argument-not-valid-type
        if not isinstance(sort_by, SortBy):
            ex_msg = f'Invalid sort_by value: {sort_by}'
            raise ValueError(ex_msg)  # noqa: TRY004

        if isinstance(sort_order, str):
            sort_order = SortOrder[sort_order.upper()]

        # pylint: disable=isinstance-second-argument-not-valid-type
        if not isinstance(sort_order, SortOrder):
            ex_msg = 'Invalid sort_order value.'
            raise ValueError(ex_msg)  # noqa: TRY004

        paths = list(self._storage_directory(cls).rglob(f'*.{self._get_file_extension}'))

        sort_order = SortOrder[sort_order.upper()] if isinstance(sort_order, str) else sort_order

        reverse = sort_order == SortOrder.DESC
        sort_by = sort_by or SortBy.INDEX
        offset = offset if offset is not None else 0

        match sort_by:
            case SortBy.MODIFIED:
                paths.sort(key=lambda x: x.stat().st_mtime, reverse=reverse)
            case SortBy.CREATED:
                try:
                    paths.sort(key=lambda x: x.stat().st_birthtime, reverse=reverse)
                except AttributeError:
                    paths.sort(key=lambda x: x.stat().st_ctime, reverse=reverse)
            case SortBy.INDEX:
                paths.sort(key=self._get_index_from_path, reverse=reverse)
            case _:
                ex_msg = 'Invalid sort_by value.'
                raise ValueError(ex_msg)
        return paths[offset : limit + offset if limit else limit]

    def load(self, cls: type[P], index_value: Any) -> P:
        """Load entity of a given class by index value."""
        paths = self._storage_directory(cls).rglob(f'{index_value}.jsondb*')
        path = next(paths, None)

        if path is None:
            ex_msg = f'Entity does not exist.  Path: {path}'
            raise FileNotFoundError(ex_msg)

        return self.load_from_path(cls, path)  # type: ignore

    def load_all(
        self,
        cls: type[P],
        *,
        where: Callable[[P], bool] | None = None,
        sort_by: SortBy | str = SortBy.INDEX,
        sort_order: SortOrder | str = SortOrder.ASC,
        offset: int = 0,
        limit: int | None = None,
    ) -> Iterable[P]:
        """Load all entities of a given class.  Sort by options are CREATED, MODIFIED, INDEX."""

        paths = self.get_paths(
            cls, sort_by=sort_by, sort_order=sort_order, offset=offset, limit=limit
        )

        target_count = limit + offset if limit is not None else len(paths)
        yielded = 0

        for p in paths:
            entity = self.load_from_path(cls, p)
            if where is None or where(entity):
                yield entity
                yielded += 1
                if yielded >= target_count:
                    break

    def load_from_path(self, clz: type[P], file_path: Path) -> P:
        """Load a model from a file path."""
        # if this is a subclass, we need to import the correct class to instantiate it.
        if file_path.parent != self._storage_directory(clz):
            module = '.'.join(file_path.parent.name.split('.')[:-1])
            class_name = file_path.parent.name.split('.')[-1]
            clz = getattr(importlib.import_module(module), class_name)

        if file_path.suffix == '.gz':
            with gz.open(file_path, 'rt', encoding='utf-8') as f:
                unserialized = json.loads(f.read())
        else:
            unserialized = json.loads(file_path.read_text(encoding='utf-8'))

        for field, model_info in clz.__fields__.items():
            if (
                isinstance(model_info.outer_type_, GenericAlias)
                and model_info.outer_type_.__origin__ == list  # noqa: E721  # TODO: @cblades
                and issubclass(model_info.type_, BaseModel)
                and not model_info.field_info.extra.get('json_db_embedded', False)
            ):
                unserialized[field] = [
                    self.load(model_info.type_, item) for item in unserialized[field]
                ]
            elif issubclass(model_info.type_, BaseModel) and not model_info.field_info.extra.get(
                'json_db_embedded', False
            ):
                unserialized[field] = self.load(model_info.type_, unserialized[field])

        return clz(**unserialized)

    @EnforceWritePolicies
    def delete(self, entity: BaseModel):
        """Delete entity from disk."""
        self._get_file_path(entity).unlink()

    @EnforceWritePolicies
    def save(self, entity: BaseModel):
        """Save entity to disk in a safe way."""
        composed_entities = []
        for field, field_info in entity.__fields__.items():
            value = getattr(entity, field)
            if isinstance(value, BaseModel) and not field_info.field_info.extra.get(
                'json_db_embedded', False
            ):
                composed_entities.append((field, self._get_index_value(value), value))
            if (
                isinstance(value, list)
                and len(value) > 0
                and isinstance(value[0], BaseModel)
                and not field_info.field_info.extra.get('json_db_embedded', False)
            ):
                composed_entities.append(
                    (field, [self._get_index_value(item) for item in value], value)
                )

        serialized = entity.dict(exclude={field[0] for field in composed_entities})
        for field_name, index_value, value in composed_entities:
            if isinstance(value, list):
                for item in value:
                    self.save(item)
            else:
                self.save(value)
            serialized[field_name] = index_value

        swap_file_path = self._get_swp_path(entity)
        file_path = self._get_file_path(entity)
        if self.gzip:
            with gz.open(swap_file_path, 'wt', encoding='utf-8') as f:
                f.write(json.dumps(serialized, indent=None, **self.json_args))
        else:
            swap_file_path.write_text(json.dumps(serialized, indent=None, **self.json_args))

        # this is atomic, and that is crucial.
        # see https://docs.python.org/3/library/pathlib.html#pathlib.Path.rename, but especially
        # https://docs.python.org/3/library/pathlib.html#pathlib.Path.rename
        swap_file_path.rename(file_path)

    def _cleanup(self):
        for path in self.path.rglob('*.lock'):
            path.unlink()

        for path in self.path.rglob('*.swp'):
            path.unlink()

    def _get_file_name(self, entity: Any) -> str:
        return f'{self._get_index_value(entity)}.{self._get_file_extension}'

    @cached_property
    def _get_file_extension(self) -> str:
        return 'jsondb.gz' if self.gzip else 'jsondb'

    def _get_file_path(self, entity: BaseModel) -> Path:
        return self._storage_directory(entity.__class__) / self._get_file_name(entity)

    def _get_index_field(self, entity: type[BaseModel]) -> str | None:
        index_field = None
        for field, value in entity.__fields__.items():
            if value.field_info.extra.get('json_db_index', False):
                index_field = field
                break
        else:
            if 'id' in entity.__fields__:
                index_field = 'id'

        if index_field is None:
            ex_msg = f'Index field is not defined for type {entity.__class__.__name__}.'
            raise TypeError(ex_msg)

        return index_field

    def _get_index_from_path(self, path: Path) -> str:
        name = path.name
        if name.endswith('.gz'):
            name = name[:-3]
        return '.'.join(name.split('.')[0:-1])

    def _get_index_value(self, entity: BaseModel):
        index_field = self._get_index_field(entity.__class__)
        if index_field is None:
            ex_msg = 'Index field is not defined.'
            raise ValueError(ex_msg)

        index = getattr(entity, index_field, None)

        if index is None:
            ex_msg = f'Index field {index_field} cannot be None.'
            raise ValueError(ex_msg)

        return index

    def _get_swp_path(self, entity: BaseModel) -> Path:
        regular_file_name = self._get_file_name(entity)
        return (
            self._storage_directory(entity.__class__) / f'{time.time_ns()}#{regular_file_name}.swp'
        )

    def _get_winning_lock_file(self, lock_files) -> Path:
        winner = None
        for lock_file in lock_files:
            parts = ''.join(lock_file.name.split('.')[:-1]).split('#')
            timestamp = float(parts[-1])
            if winner is None or timestamp < winner[0]:  # pylint: disable=unsubscriptable-object
                winner = (timestamp, lock_file)

        return winner[1]  # type: ignore # pylint: disable=unsubscriptable-object

    def _migrate_gzip(self):
        """Migrate existing files to or from gzip.

        This only really matters when the gzip flag is changed across runs.
        """
        if self.gzip:
            for path in self.path.rglob('*.jsondb'):
                gz.open(  # noqa: SIM115
                    path.with_suffix('.jsondb.gz'), 'wt', encoding='utf-8'
                ).write(path.read_text(encoding='utf-8'))
                path.unlink()
        else:
            for path in self.path.rglob('*.jsondb.gz'):
                path.with_suffix('.jsondb').write_text(
                    gz.open(path, 'rt', encoding='utf-8').read()  # noqa: SIM115
                )
                path.unlink()

    @lru_cache(maxsize=20)  # noqa: B019
    def _storage_directory(self, clz: type[P]) -> Path:
        if len(clz.__bases__) == 0:
            directory = self.path
        elif clz.__bases__[0] != BaseModel:
            directory = self._storage_directory(clz.__bases__[0])  # type: ignore
        else:
            directory = self.path

        directory = directory / JsonDB._type_slug(clz)  # type: ignore
        if directory.exists() and not directory.is_dir():
            ex_msg = f'File {directory} exists and is not a directory.'
            raise ValueError(ex_msg)

        directory.mkdir(parents=True, exist_ok=True)

        return directory

    @staticmethod
    def _type_slug(clz) -> str:
        return f'{clz.__module__}.{clz.__name__}'

    @property
    def _pydantic(self) -> BaseModel:
        return cast(BaseModel, self)
