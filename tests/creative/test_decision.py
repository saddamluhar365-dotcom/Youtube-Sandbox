from app.channel.models import ChannelIdentity, PublicChannel, PublicVideo
from app.channel.analyzer import ChannelAnalyzer
from app.intelligence.db import Database
from app.intelligence.recipe_master import RecipeCandidate, RecipeMaster
from app.competitors.gap import GapReport
from app.creative.decision import CreativeDirector


def _analysis(tmp_path):
    channel = PublicChannel(
        identity=ChannelIdentity(
            channel_id="UC12345678901234567890",
            channel_handle="@owned",
            channel_url="https://youtube.com/@owned",
        ),
        videos=(
            PublicVideo("v1", "Secret Village Potato Recipe #food", duration_seconds=45, view_count=1000),
            PublicVideo("v2", "Traditional Chutney", duration_seconds=55, view_count=800),
        ),
    )
    return ChannelAnalyzer().analyze(channel)


def test_select_recipe_uses_explicit_scoring_inputs_and_locks(tmp_path):
    db = Database(tmp_path / "intel.db")
    db.initialize()
    master = RecipeMaster(db)
    existing = RecipeCandidate(
        name="Potato Curry",
        ingredients=["potato", "onion", "tomato"],
        main_ingredient="potato",
        cooking_method="slow cook",
    )
    master.register(existing)

    candidate = RecipeCandidate(
        name="Raw Mango Chutney",
        ingredients=["raw mango", "chili", "salt"],
        main_ingredient="raw mango",
        cooking_method="grind",
        region="Gujarat",
        story_angle="forgotten village summer food",
        visual_concept="stone grinding in a courtyard",
        asmr_elements=["grinding", "birds", "leaves"],
    )

    director = CreativeDirector(master)
    decision = director.select_recipe(
        [candidate],
        demand_signals={"raw mango chutney": 0.8},
        feasibility_signals={"raw mango chutney": 0.9},
        uniqueness_signals={"raw mango chutney": 1.0},
        gap_report=GapReport(status="observed", owned_channel_id="UC12345678901234567890", peer_count=2),
    )

    assert decision.status == "LOCKED"
    assert decision.recipe.name == "Raw Mango Chutney"
    assert decision.score_breakdown["uniqueness"] == 1.0
    assert decision.locked_at is not None


def test_select_recipe_rejects_recipe_master_duplicate(tmp_path):
    db = Database(tmp_path / "intel.db")
    db.initialize()
    master = RecipeMaster(db)
    master.register(
        RecipeCandidate(
            name="Potato Curry",
            ingredients=["aloo", "pyaz", "tamatar"],
            main_ingredient="aloo",
            cooking_method="slow cook",
        )
    )

    director = CreativeDirector(master)
    candidate = RecipeCandidate(
        name="Village Aloo Sabzi",
        ingredients=["potato", "onion", "tomato"],
        main_ingredient="potato",
        cooking_method="slow cook",
    )

    try:
        director.select_recipe([candidate])
    except ValueError as exc:
        assert "unique" in str(exc).lower()
    else:
        raise AssertionError("duplicate recipe must not be selected")


def test_world_and_story_are_locked_only_after_required_inputs():
    director = CreativeDirector(None)
    world = director.build_world(
        location="Kutch village courtyard",
        season="summer",
        weather="warm evening",
        kitchen="mud-plastered outdoor kitchen",
        character={"age_appearance": "adult", "clothing": "simple Indian village attire"},
    )
    story = director.build_story(
        hook="A forgotten village dish appears before sunset.",
        origin="A recipe preserved through generations.",
        discovery="The unusual ingredient is revealed in the courtyard.",
        transformation="Grinding and cooking transform it into the final dish.",
        reveal="The finished dish is revealed with a quiet ASMR payoff.",
    )

    assert world.status == "LOCKED"
    assert story.status == "LOCKED"
    assert "Kutch" in world.location
    assert len(story.beats) == 5
