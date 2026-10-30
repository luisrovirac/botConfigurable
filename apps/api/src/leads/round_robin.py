class RoundRobin:
    def assign(self, agents: list[str]) -> str | None:
        if not agents:
            return None
        return agents[0]
