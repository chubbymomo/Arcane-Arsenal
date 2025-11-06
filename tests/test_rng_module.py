"""
Tests for RNG module.
"""

import pytest
from src.modules.rng.dice_parser import DiceParser, DiceNotationError
from src.modules.rng.roller import DiceRoller
from src.modules.rng import RNGModule
from src.core.state_engine import StateEngine
from src.core.event_bus import Event
import tempfile
import os


class TestDiceParser:
    """Test dice notation parser."""

    def test_simple_roll(self):
        """Test parsing simple dice notation."""
        parsed = DiceParser.parse("1d20")
        assert len(parsed.dice_groups) == 1
        assert parsed.dice_groups[0].count == 1
        assert parsed.dice_groups[0].sides == 20
        assert parsed.static_modifier == 0

    def test_roll_with_modifier(self):
        """Test parsing with static modifier."""
        parsed = DiceParser.parse("1d20+5")
        assert len(parsed.dice_groups) == 1
        assert parsed.static_modifier == 5

        parsed = DiceParser.parse("1d20-3")
        assert parsed.static_modifier == -3

    def test_multiple_dice(self):
        """Test parsing multiple dice."""
        parsed = DiceParser.parse("3d6")
        assert parsed.dice_groups[0].count == 3
        assert parsed.dice_groups[0].sides == 6

    def test_complex_expression(self):
        """Test parsing complex expressions."""
        parsed = DiceParser.parse("2d8+1d6+3")
        assert len(parsed.dice_groups) == 2
        assert parsed.dice_groups[0].count == 2
        assert parsed.dice_groups[0].sides == 8
        assert parsed.dice_groups[1].count == 1
        assert parsed.dice_groups[1].sides == 6
        assert parsed.static_modifier == 3

    def test_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        parsed1 = DiceParser.parse("1d20")
        parsed2 = DiceParser.parse("1D20")
        assert parsed1.dice_groups[0].sides == parsed2.dice_groups[0].sides

    def test_whitespace_handling(self):
        """Test that whitespace is ignored."""
        parsed = DiceParser.parse(" 1d20 + 5 ")
        assert parsed.dice_groups[0].count == 1
        assert parsed.static_modifier == 5

    def test_invalid_notation(self):
        """Test that invalid notation raises error."""
        with pytest.raises(DiceNotationError):
            DiceParser.parse("")

        with pytest.raises(DiceNotationError):
            DiceParser.parse("invalid")

        with pytest.raises(DiceNotationError):
            DiceParser.parse("0d20")  # Zero dice

        with pytest.raises(DiceNotationError):
            DiceParser.parse("1d0")  # Zero sides

    def test_validation(self):
        """Test notation validation."""
        assert DiceParser.validate("1d20")
        assert DiceParser.validate("3d6+5")
        assert not DiceParser.validate("invalid")
        assert not DiceParser.validate("")


class TestDiceRoller:
    """Test dice roller with seeded random."""

    def test_simple_roll(self):
        """Test simple roll."""
        roller = DiceRoller(seed=42)
        result = roller.roll("1d20")

        assert result.notation == "1d20"
        assert 1 <= result.total <= 20
        assert len(result.dice_results) == 1
        assert len(result.dice_results[0].rolls) == 1

    def test_roll_with_modifier(self):
        """Test roll with static modifier."""
        roller = DiceRoller(seed=42)
        result = roller.roll("1d20+5")

        assert result.static_modifier == 5
        assert result.total == result.dice_results[0].total + 5

    def test_multiple_dice(self):
        """Test rolling multiple dice."""
        roller = DiceRoller(seed=42)
        result = roller.roll("3d6")

        assert len(result.dice_results[0].rolls) == 3
        assert all(1 <= r <= 6 for r in result.dice_results[0].rolls)

    def test_advantage(self):
        """Test advantage mechanic."""
        roller = DiceRoller(seed=42)
        result = roller.roll("1d20", advantage=True)

        assert result.advantage is True
        assert result.advantage_rolls is not None
        assert len(result.advantage_rolls) == 2
        # Result should be the higher of the two rolls
        assert result.dice_results[0].rolls[0] == max(result.advantage_rolls)

    def test_disadvantage(self):
        """Test disadvantage mechanic."""
        roller = DiceRoller(seed=42)
        result = roller.roll("1d20", disadvantage=True)

        assert result.disadvantage is True
        assert result.advantage_rolls is not None
        assert len(result.advantage_rolls) == 2
        # Result should be the lower of the two rolls
        assert result.dice_results[0].rolls[0] == min(result.advantage_rolls)

    def test_advantage_and_disadvantage_error(self):
        """Test that both advantage and disadvantage raises error."""
        roller = DiceRoller(seed=42)
        with pytest.raises(ValueError):
            roller.roll("1d20", advantage=True, disadvantage=True)

    def test_seeded_determinism(self):
        """Test that seeded roller produces same results."""
        roller1 = DiceRoller(seed=12345)
        roller2 = DiceRoller(seed=12345)

        result1 = roller1.roll("3d6+5")
        result2 = roller2.roll("3d6+5")

        assert result1.total == result2.total
        assert result1.dice_results[0].rolls == result2.dice_results[0].rolls

    def test_critical_success(self):
        """Test natural 20 detection."""
        roller = DiceRoller(seed=42)

        # Roll many times until we get a nat 20
        found_nat_20 = False
        for _ in range(100):
            result = roller.roll("1d20")
            if result.natural_20:
                found_nat_20 = True
                assert 20 in result.dice_results[0].rolls
                break

        # With 100 rolls, we should find at least one nat 20
        assert found_nat_20

    def test_critical_failure(self):
        """Test natural 1 detection."""
        roller = DiceRoller(seed=42)

        # Roll many times until we get a nat 1
        found_nat_1 = False
        for _ in range(100):
            result = roller.roll("1d20")
            if result.natural_1:
                found_nat_1 = True
                assert 1 in result.dice_results[0].rolls
                break

        # With 100 rolls, we should find at least one nat 1
        assert found_nat_1

    def test_breakdown(self):
        """Test breakdown string generation."""
        roller = DiceRoller(seed=42)
        result = roller.roll("2d6+3")

        breakdown = result.get_breakdown()
        assert "2d6" in breakdown
        assert "3" in breakdown or "+3" in breakdown
        assert str(result.total) in breakdown

    def test_to_dict(self):
        """Test conversion to dictionary."""
        roller = DiceRoller(seed=42)
        result = roller.roll("1d20+5")

        data = result.to_dict()
        assert data['notation'] == "1d20+5"
        assert data['total'] == result.total
        assert 'breakdown' in data
        assert isinstance(data['dice_results'], list)


class TestRNGModule:
    """Test RNG module integration with engine."""

    @pytest.fixture
    def temp_world(self):
        """Create temporary world for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world_path = os.path.join(tmpdir, "test_world")
            yield world_path

    def test_module_registration(self, temp_world):
        """Test that module registers components and events."""
        # Create engine with RNG module
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Check components registered
        component_types = [ct['type'] for ct in engine.storage.get_component_types()]
        assert 'Luck' in component_types
        assert 'RollModifier' in component_types

        # Check events registered
        event_types = [et['type'] for et in engine.storage.get_event_types()]
        assert 'roll.requested' in event_types
        assert 'roll.completed' in event_types

    def test_roll_request_event(self, temp_world):
        """Test processing roll request via events."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create test entity
        result = engine.create_entity("Test Character")
        assert result.success
        entity_id = result.data['id']

        # Subscribe to roll results
        results = []

        def capture_result(event: Event):
            results.append(event)

        engine.event_bus.subscribe('roll.completed', capture_result)

        # Request a roll
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20+5',
                'roll_type': 'attack',
                'purpose': 'Attack test'
            }
        ))

        # Check result was published
        assert len(results) == 1
        result_event = results[0]
        assert result_event.event_type == 'roll.completed'
        assert result_event.data['entity_id'] == entity_id
        assert result_event.data['roll_type'] == 'attack'
        assert 1 + 5 <= result_event.data['total'] <= 20 + 5

    def test_luck_component_global_bonus(self, temp_world):
        """Test that Luck component applies global bonus."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create entity with luck
        result = engine.create_entity("Lucky Character")
        assert result.success
        entity_id = result.data['id']
        engine.add_component(entity_id, "Luck", {
            "global_bonus": 3,
            "advantage_on": [],
            "disadvantage_on": [],
            "reroll_ones": False,
            "critical_range": 20
        })

        # Subscribe to results
        results = []

        def capture_result(event: Event):
            results.append(event)

        engine.event_bus.subscribe('roll.completed', capture_result)

        # Request roll
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20',
                'roll_type': 'attack',
                'purpose': 'Test'
            }
        ))

        # Check that bonus was applied
        assert len(results) == 1
        result = results[0]
        # Original was 1d20, should be modified to 1d20+3
        assert 1 + 3 <= result.data['total'] <= 20 + 3
        # Check modifiers were tracked
        assert any(
            m['source'] == 'Luck' and m['bonus'] == 3
            for m in result.data['modifiers_applied']
        )

    def test_luck_component_advantage(self, temp_world):
        """Test that Luck component grants advantage."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create entity with advantage on attack rolls
        result = engine.create_entity("Advantaged Character")
        assert result.success
        entity_id = result.data['id']
        engine.add_component(entity_id, "Luck", {
            "global_bonus": 0,
            "advantage_on": ["attack"],
            "disadvantage_on": [],
            "reroll_ones": False,
            "critical_range": 20
        })

        # Subscribe to results
        results = []

        def capture_result(event: Event):
            results.append(event)

        engine.event_bus.subscribe('roll.completed', capture_result)

        # Request attack roll
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20',
                'roll_type': 'attack',
                'purpose': 'Test'
            }
        ))

        # Check advantage was applied
        assert len(results) == 1
        result = results[0]
        assert result.data['advantage'] is True

    def test_roll_modifier_component(self, temp_world):
        """Test that RollModifier component applies bonuses."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create entity with roll modifier
        result = engine.create_entity("Buffed Character")
        assert result.success
        entity_id = result.data['id']
        engine.add_component(entity_id, "RollModifier", {
            "modifier_type": "attack",
            "bonus": 5,
            "source": "Magic Sword",
            "conditions": {}
        })

        # Subscribe to results
        results = []

        def capture_result(event: Event):
            results.append(event)

        engine.event_bus.subscribe('roll.completed', capture_result)

        # Request attack roll
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20',
                'roll_type': 'attack',
                'purpose': 'Test'
            }
        ))

        # Check modifier was applied
        assert len(results) == 1
        result = results[0]
        assert 1 + 5 <= result.data['total'] <= 20 + 5
        assert any(
            m['source'] == 'Magic Sword' and m['bonus'] == 5
            for m in result.data['modifiers_applied']
        )


    def test_roll_type_validation(self, temp_world):
        """Test that invalid roll types are rejected."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create test entity
        result = engine.create_entity("Test Character")
        assert result.success
        entity_id = result.data['id']

        # Subscribe to results
        results = []

        def capture_result(event: Event):
            results.append(event)

        engine.event_bus.subscribe('roll.completed', capture_result)

        # Request roll with INVALID roll_type
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20',
                'roll_type': 'invalid_type_not_registered',  # Invalid!
                'purpose': 'Test'
            }
        ))

        # Roll should be rejected - no result event
        assert len(results) == 0

        # Request roll with VALID roll_type
        engine.event_bus.publish(Event.create(
            event_type='roll.requested',
            entity_id=entity_id,
            actor_id=entity_id,
            data={
                'entity_id': entity_id,
                'notation': '1d20',
                'roll_type': 'attack',  # Valid!
                'purpose': 'Test'
            }
        ))

        # Valid roll should succeed
        assert len(results) == 1
        assert results[0].data['roll_type'] == 'attack'

    def test_get_roll_types(self, temp_world):
        """Test getting registered roll types."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Get all roll types
        roll_types = engine.storage.get_roll_types()

        # Should have core roll types from RNG module
        type_names = {rt['type'] for rt in roll_types}
        assert 'attack' in type_names
        assert 'damage' in type_names
        assert 'saving_throw' in type_names
        assert 'skill_check' in type_names
        assert 'initiative' in type_names
        assert 'ability_check' in type_names

        # Check they have proper structure
        for rt in roll_types:
            assert 'type' in rt
            assert 'description' in rt
            assert 'module' in rt
            assert 'category' in rt
            assert rt['module'] == 'rng'


    def test_component_validation(self, temp_world):
        """Test that component validation rejects invalid roll types."""
        engine = StateEngine.initialize_world(
            world_path=temp_world,
            world_name="Test World",
            modules=['rng']
        )

        # Create test entity
        result = engine.create_entity("Test Character")
        assert result.success
        entity_id = result.data['id']

        # Try to add RollModifier with INVALID roll type
        result = engine.add_component(entity_id, "RollModifier", {
            "modifier_type": "invalid_type",  # Not registered!
            "bonus": 5,
            "source": "Test"
        })

        # Should fail validation
        assert not result.success
        assert "Invalid modifier_type" in result.error

        # Try to add Luck with INVALID roll type in advantage_on
        result = engine.add_component(entity_id, "Luck", {
            "global_bonus": 0,
            "advantage_on": ["invalid_type"],  # Not registered!
            "disadvantage_on": [],
            "reroll_ones": False,
            "critical_range": 20
        })

        # Should fail validation
        assert not result.success
        assert "Invalid roll type in advantage_on" in result.error

        # Now with VALID roll types - should succeed
        result = engine.add_component(entity_id, "Luck", {
            "global_bonus": 0,
            "advantage_on": ["attack", "saving_throw"],  # Valid!
            "disadvantage_on": [],
            "reroll_ones": False,
            "critical_range": 20
        })

        assert result.success


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
