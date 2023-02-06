from typing import Protocol, Set, Callable, Optional

from pathlib import Path
import shutil
import subprocess

class Artifact(Protocol):
    def up_to_date(self) -> bool:
        pass

    def builder(self) -> Optional["Builder"]:
        pass

class Builder(Protocol):
    def prerequisite(self) -> Set[Artifact]:
        pass

    def run(self) -> Set[Artifact]:
        pass

class File(Artifact, Protocol):
    def path(self) -> Path:
        pass

class TouchFile():
    def _typecheck(self) -> Builder:
        return self

    def __init__(self, path: Path):
        self._path = path

    def run(self) -> Set[Artifact]:
        self._path.touch()
        return {RegularFile(self._path)}

    def prerequisite(self) -> Set[Artifact]:
        return set()

class ToTouchFile():
    def _typecheck(self) -> Artifact:
        return self
    
    def _typecheck2(self) -> File:
        return self

    def __init__(self, path: Path) -> None:
        self._path = path

    def up_to_date(self) -> bool:
        return False

    def builder(self) -> Builder:
        return TouchFile(self._path)

    def path(self) -> Path:
        return self._path

class RegularFile():
    def _typecheck(self) -> File:
        return self

    def __init__(self, path: Path) -> None:
        self._path = path
        self._mtime = path.stat().st_mtime_ns

    def up_to_date(self) -> bool:
        mtime = self._path.stat().st_mtime_ns
        new = mtime > self._mtime
        self._mtime = mtime
        return new

    def builder(self):
        return None

    def path(self) -> Path:
        return self._path


class OutputFile():
    def __init__(self, path: Path, builder: Callable[[Path], Builder]) -> None:
        self._path = path
        self._builder = builder(self._path)
        self._mtime: Optional[int] = None
        if self._path.is_file():
            self._mtime = path.stat().st_mtime_ns
        
    def up_to_date(self) -> bool:
        if not self._path.is_file():
            return False

        mtime = self._path.stat().st_mtime_ns
        if not self._mtime:
            self._mtime = mtime
            return True 

        new = mtime > self._mtime
        self._mtime = mtime
        return new

    def builder(self) -> Optional[Builder]:
        return self._builder

def gcc(input: File) -> Callable[[Path], Builder]:
    def f(output: Path) -> Builder:
        return GCC(input, output)
    return f

class GCC():
    def __init__(self, input: File, output: Path) -> None:
        self._input = input
        self._output = output

    def prerequisite(self) -> Set[Artifact]:
        return {self._input}

    def run(self) -> Set[Artifact]:
        gcc = shutil.which("gcc")
        assert gcc is not None
        gccProcess = subprocess.Popen([gcc, self._input.path(), "-o", self._output])
        if gccProcess.wait() != 0:
            raise Exception("Error in running GCC")
        return {RegularFile(self._output)}

a = OutputFile(Path("foo"), gcc(ToTouchFile(Path("foo.c"))))

def builder(b: Artifact):
    if b.up_to_date():
        print("aaa")
        return

    bb = b.builder()
    if not bb:
        return

    for p in bb.prerequisite():
        builder(p)

    bb.run()

builder(a)