from __future__ import annotations

from collections import deque
from pathlib import Path


class FileTaskQueue:
    def __init__(self, queue_path: str | Path, visited_path: str | Path):
        self.queue_path = Path(queue_path)
        self.visited_path = Path(visited_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.visited_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue = deque(self._load_lines(self.queue_path))
        self.visited = set(self._load_lines(self.visited_path))

    @staticmethod
    def _load_lines(path: Path) -> list[str]:
        if not path.exists():
            return []
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]

    def pop(self) -> str | None:
        while self.queue:
            url = self.queue.popleft()
            if url not in self.visited:
                return url
        return None

    def push_many(self, urls: list[str]) -> int:
        added = 0
        current = set(self.queue)
        for url in urls:
            if url and url not in self.visited and url not in current:
                self.queue.append(url)
                current.add(url)
                added += 1
        self.flush_queue()
        return added

    def mark_visited(self, url: str) -> None:
        self.visited.add(url)
        with self.visited_path.open("a", encoding="utf-8") as file:
            file.write(url + "\n")
        self.flush_queue()

    def flush_queue(self) -> None:
        self.queue_path.write_text("\n".join(self.queue) + ("\n" if self.queue else ""), encoding="utf-8")