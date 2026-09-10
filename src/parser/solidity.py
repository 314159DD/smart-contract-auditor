"""Solidity source code parser using regex-based AST extraction."""
import re
import os

from .models import Contract, Function, StateVariable, Modifier, Event, Parameter


class SolidityParser:
    VISIBILITY = frozenset({"public", "external", "internal", "private"})
    MUTABILITY = frozenset({"view", "pure", "payable"})

    def parse_file(self, path: str) -> list:
        """Parse a .sol file; returns all Contract objects found."""
        with open(path, encoding="utf-8") as f:
            source = f.read()
        contracts = self.parse(source)
        for c in contracts:
            c.file_path = path
        return contracts

    def parse(self, source: str) -> list:
        """Parse Solidity source string into Contract objects."""
        pragma = self._extract_pragma(source)
        ver = self._parse_compiler_version(pragma)
        imports = self._extract_imports(source)
        return self._extract_contracts(source, ver, pragma, imports)

    def _extract_pragma(self, source: str) -> str:
        m = re.search(r"pragma\s+solidity\s+([^;]+);", source)
        return m.group(0) if m else ""

    def _parse_compiler_version(self, pragma: str) -> str:
        m = re.search(r"(\d+\.\d+\.\d+)", pragma)
        return m.group(1) if m else "0.8.0"

    def _extract_imports(self, source: str) -> list:
        return re.findall(r"import\s+[^;]+;", source)

    def _extract_contracts(self, source, ver, pragma, imports):
        contracts = []
        pat = re.compile(
            r"(abstract\s+)?(contract|interface|library)\s+(\w+)"
            r"(?:\s+is\s+([\w\s,]+?))?\s*\{",
            re.MULTILINE,
        )
        for m in pat.finditer(source):
            inh = [i.strip() for i in (m.group(4) or "").split(",") if i.strip()]
            body = self._extract_block(source, m.end() - 1)
            c = Contract(
                name=m.group(3), source=body, compiler_version=ver,
                pragma=pragma, imports=imports, inheritance=inh,
                is_interface=(m.group(2) == "interface"),
                is_abstract=bool(m.group(1)),
            )
            c.functions = self._extract_functions(body)
            c.state_variables = self._extract_state_variables(body)
            c.modifiers = self._extract_modifiers(body)
            c.events = self._extract_events(body)
            contracts.append(c)
        return contracts

    def _extract_block(self, source: str, pos: int) -> str:
        """Return text from pos up to and including the matching closing brace."""
        depth, i = 0, pos
        while i < len(source):
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
                if depth == 0:
                    return source[pos : i + 1]
            i += 1
        return source[pos:]

    def _extract_functions(self, source: str) -> list:
        fns = []
        pat = re.compile(
            r"\b(function|constructor|fallback|receive)\s*(\w*)\s*\(([^)]*)\)"
            r"([^{;]*)(?:\breturns\s*\(([^)]*)\))?\s*(?:;|\{)",
            re.MULTILINE | re.DOTALL,
        )
        for m in pat.finditer(source):
            kind = m.group(1)
            name = m.group(2) or kind
            q = m.group(4) or ""
            vis = next((v for v in self.VISIBILITY if re.search(r"\b" + v + r"\b", q)), "internal")
            mut = next((x for x in self.MUTABILITY if re.search(r"\b" + x + r"\b", q)), "nonpayable")
            skip = self.VISIBILITY | self.MUTABILITY | {"returns", "override", "virtual"}
            mods = [w for w in re.findall(r"\b(\w+)\b", q) if w not in skip]
            fn = Function(
                name=name, visibility=vis, mutability=mut, modifiers=mods,
                parameters=self._parse_params(m.group(3)),
                returns=self._parse_params(m.group(5) or ""),
                is_constructor=(kind == "constructor"),
            )
            bs = source.find("{", m.start())
            if bs != -1:
                b = self._extract_block(source, bs)
                fn.body_source = b
                fn.line_start = source[:m.start()].count("\n") + 1
                fn.line_end = source[:bs + len(b)].count("\n") + 1
            fns.append(fn)
        return fns

    def _parse_params(self, s: str) -> list:
        if not s.strip():
            return []
        params = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            if len(tokens) >= 2:
                params.append(Parameter(type=tokens[0], name=tokens[-1]))
            elif tokens:
                params.append(Parameter(type=tokens[0], name=""))
        return params

    def _extract_state_variables(self, source: str) -> list:
        vars_ = []
        pat = re.compile(
            r"^\s+((?:mapping|address|uint\w*|int\w*|bool|bytes\w*|string|[\w\[\]]+)"
            r"(?:\[\])*)\s+(public|private|internal|constant|immutable|\s)*(\w+)\s*"
            r"(?:=\s*([^;]+))?;",
            re.MULTILINE,
        )
        for m in pat.finditer(source):
            q = m.group(2) or ""
            vis = next((v for v in self.VISIBILITY if v in q), "internal")
            vars_.append(StateVariable(
                name=m.group(3), type=m.group(1), visibility=vis,
                is_constant="constant" in q,
                is_immutable="immutable" in q,
                initial_value=(m.group(4) or "").strip() or None,
                line=source[:m.start()].count("\n") + 1,
            ))
        return vars_

    def _extract_modifiers(self, source: str) -> list:
        mods = []
        pat = re.compile(r"\bmodifier\s+(\w+)\s*\(([^)]*)\)\s*\{", re.MULTILINE)
        for m in pat.finditer(source):
            body = self._extract_block(source, m.end() - 1)
            mods.append(Modifier(
                name=m.group(1),
                parameters=self._parse_params(m.group(2)),
                body_source=body,
                line_start=source[:m.start()].count("\n") + 1,
            ))
        return mods

    def _extract_events(self, source: str) -> list:
        events = []
        pat = re.compile(r"\bevent\s+(\w+)\s*\(([^)]*)\)\s*;", re.MULTILINE)
        for m in pat.finditer(source):
            params = []
            for part in m.group(2).split(","):
                tokens = part.strip().split()
                indexed = "indexed" in tokens
                tokens = [t for t in tokens if t != "indexed"]
                if len(tokens) >= 2:
                    params.append(Parameter(type=tokens[0], name=tokens[-1], indexed=indexed))
            events.append(Event(
                name=m.group(1), parameters=params,
                line=source[:m.start()].count("\n") + 1,
            ))
        return events

    def resolve_imports(self, source: str, base_path: str) -> str:
        """Attempt to inline local imports."""
        def rep(m):
            p = m.group(1)
            if p.startswith("@") or p.startswith("http"):
                return m.group(0)
            fp = os.path.join(base_path, p)
            return open(fp).read() if os.path.exists(fp) else m.group(0)
        return re.sub(r'import\s+"([^"]+)";', rep, source)
