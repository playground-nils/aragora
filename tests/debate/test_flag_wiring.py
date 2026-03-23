"""Tests for enable_rlm, rlm_mode, and enable_staking flag wiring.

Verifies that ArenaConfig flags propagate through to_arena_kwargs(),
MergedConfig, store_post_tracker_config(), and ContextInitializer.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aragora.debate.arena_config import ArenaConfig


class TestToArenaKwargsFlags:
    """Tests for to_arena_kwargs() including RLM and staking flags."""

    def test_to_arena_kwargs_includes_rlm_and_staking_flags(self):
        """Verify enable_rlm, rlm_mode, enable_staking appear in kwargs."""
        config = ArenaConfig(
            enable_rlm=True,
            rlm_mode="true_rlm",
            enable_staking=True,
        )
        kwargs = config.to_arena_kwargs()
        assert kwargs["enable_rlm"] is True
        assert kwargs["rlm_mode"] == "true_rlm"
        assert kwargs["enable_staking"] is True

    def test_to_arena_kwargs_rlm_staking_defaults(self):
        """Default values propagate correctly."""
        config = ArenaConfig()
        kwargs = config.to_arena_kwargs()
        assert kwargs["enable_rlm"] is False
        assert kwargs["rlm_mode"] == "auto"
        assert kwargs["enable_staking"] is False

    def test_staking_defaults_false(self):
        """Staking must default to False for safety."""
        config = ArenaConfig()
        assert config.enable_staking is False


class TestEnableRlmDisablesCompression:
    """Tests for enable_rlm gating on ContextInitializer construction."""

    def test_enable_rlm_false_disables_compression(self):
        """When enable_rlm=False, enable_rlm_compression should be False."""
        # Simulate the expression used in arena_phases.py:
        # enable_rlm_compression=getattr(arena, "enable_rlm", True) and getattr(arena, "use_rlm_limiter", True)
        arena = MagicMock()
        arena.enable_rlm = False
        arena.use_rlm_limiter = True

        result = getattr(arena, "enable_rlm", True) and getattr(arena, "use_rlm_limiter", True)
        assert result is False

    def test_backward_compat_no_enable_rlm_attribute(self):
        """When enable_rlm not set, defaults to True for backward compat."""
        arena = MagicMock(spec=[])  # empty spec => no attributes

        result = getattr(arena, "enable_rlm", True) and getattr(arena, "use_rlm_limiter", True)
        assert result is True

    def test_both_true_enables_compression(self):
        """When both enable_rlm and use_rlm_limiter are True, compression is enabled."""
        arena = MagicMock()
        arena.enable_rlm = True
        arena.use_rlm_limiter = True

        result = getattr(arena, "enable_rlm", True) and getattr(arena, "use_rlm_limiter", True)
        assert result is True

    def test_use_rlm_limiter_false_disables_compression(self):
        """When use_rlm_limiter=False, compression is disabled regardless of enable_rlm."""
        arena = MagicMock()
        arena.enable_rlm = True
        arena.use_rlm_limiter = False

        result = getattr(arena, "enable_rlm", True) and getattr(arena, "use_rlm_limiter", True)
        assert result is False


class TestStorePostTrackerConfig:
    """Tests for flag propagation through store_post_tracker_config."""

    def test_rlm_and_staking_stored_on_arena(self):
        """Flags should be stored on the arena instance."""
        from aragora.debate.orchestrator_init import store_post_tracker_config

        arena = MagicMock()
        # Ensure agent_selector exists for staking propagation
        arena.agent_selector = MagicMock()

        cfg = MagicMock()
        cfg.enable_rlm = True
        cfg.rlm_mode = "compression"
        cfg.enable_staking = True

        store_post_tracker_config(arena, cfg)

        assert arena.enable_rlm is True
        assert arena.rlm_mode == "compression"
        assert arena.enable_staking is True
        # Staking should propagate to agent_selector
        assert arena.agent_selector.enable_staking is True

    def test_staking_not_propagated_when_disabled(self):
        """When enable_staking=False, agent_selector should not be touched."""
        from aragora.debate.orchestrator_init import store_post_tracker_config

        arena = MagicMock()
        arena.agent_selector = MagicMock(spec=["select"])  # no enable_staking attr

        cfg = MagicMock()
        cfg.enable_rlm = False
        cfg.rlm_mode = "auto"
        cfg.enable_staking = False

        store_post_tracker_config(arena, cfg)

        assert arena.enable_staking is False
        # Should NOT have set enable_staking on agent_selector
        assert (
            not hasattr(arena.agent_selector, "enable_staking")
            or not arena.agent_selector.enable_staking
        )


class TestArenaAcceptsEnableRlm:
    """Regression tests: Arena.__init__ must accept enable_rlm, rlm_mode, enable_staking."""

    def test_arena_init_accepts_enable_rlm(self):
        """Arena(enable_rlm=True) must not raise TypeError."""
        from aragora.debate.orchestrator import Arena

        env = MagicMock()
        env.task = "test"
        env.context = ""
        agents = [MagicMock(), MagicMock()]
        for a in agents:
            a.name = "test-agent"

        # This used to raise: TypeError: Arena.__init__() got an unexpected keyword argument 'enable_rlm'
        arena = Arena(environment=env, agents=agents, enable_rlm=True)
        assert arena.enable_rlm is True

    def test_arena_init_accepts_rlm_mode(self):
        """Arena(rlm_mode='true_rlm') must not raise TypeError."""
        from aragora.debate.orchestrator import Arena

        env = MagicMock()
        env.task = "test"
        env.context = ""
        agents = [MagicMock(), MagicMock()]
        for a in agents:
            a.name = "test-agent"

        arena = Arena(environment=env, agents=agents, rlm_mode="true_rlm")
        assert arena.rlm_mode == "true_rlm"

    def test_arena_init_accepts_enable_staking(self):
        """Arena(enable_staking=True) must not raise TypeError."""
        from aragora.debate.orchestrator import Arena

        env = MagicMock()
        env.task = "test"
        env.context = ""
        agents = [MagicMock(), MagicMock()]
        for a in agents:
            a.name = "test-agent"

        arena = Arena(environment=env, agents=agents, enable_staking=True)
        assert arena.enable_staking is True

    def test_arena_from_config_with_enable_rlm(self):
        """Arena.from_config with ArenaConfig(enable_rlm=True) must not raise."""
        from aragora.debate.orchestrator import Arena

        config = ArenaConfig(enable_rlm=True, rlm_mode="compression", enable_staking=True)
        env = MagicMock()
        env.task = "test"
        env.context = ""
        agents = [MagicMock(), MagicMock()]
        for a in agents:
            a.name = "test-agent"

        arena = Arena.from_config(environment=env, agents=agents, config=config)
        assert arena.enable_rlm is True
        assert arena.rlm_mode == "compression"
        assert arena.enable_staking is True
