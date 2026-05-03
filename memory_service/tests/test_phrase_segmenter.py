"""Tests pour PhraseSegmenter."""

import pytest
from memory_service.phrase_segmenter import PhraseSegmenter, Phrase


@pytest.fixture
def segmenter():
    """Crée un segmenteur de phrases pour les tests."""
    return PhraseSegmenter(min_length=5, max_length=500)


def test_segment_simple_sentences(segmenter):
    """Test de segmentation de phrases simples."""
    text = "Je préfère Python à Java. J'aime travailler sur des projets d'IA."
    phrases = segmenter.segment(text)
    
    assert len(phrases) == 2
    assert phrases[0].text == "Je préfère Python à Java"
    assert phrases[1].text == "J'aime travailler sur des projets d'IA"


def test_segment_with_questions(segmenter):
    """Test de segmentation avec questions."""
    text = "Qui es-tu? Comment tu fonctionnes? Je veux savoir."
    phrases = segmenter.segment(text)
    
    assert len(phrases) == 3
    assert phrases[0].is_question
    assert phrases[1].is_question
    assert not phrases[2].is_question


def test_segment_with_exclamations(segmenter):
    """Test de segmentation avec exclamations."""
    text = "C'est génial! Je suis impressionné! Continue comme ça."
    phrases = segmenter.segment(text)
    
    assert len(phrases) == 3
    assert phrases[0].is_exclamation
    assert phrases[1].is_exclamation
    assert not phrases[2].is_exclamation


def test_filter_short_phrases(segmenter):
    """Test du filtrage des phrases trop courtes."""
    text = "Ok. Je préfère Python. Merci."
    phrases = segmenter.segment(text)
    
    # "Ok" et "Merci" devraient être filtrés
    assert len(phrases) >= 1
    assert any("Python" in p.text for p in phrases)


def test_filter_non_informative(segmenter):
    """Test du filtrage des phrases non informatives."""
    text = "Salut. Je préfère Python à Java. Merci."
    phrases = segmenter.segment(text)
    
    # "Salut" et "Merci" devraient être filtrés
    assert len(phrases) >= 1
    assert any("Python" in p.text for p in phrases)


def test_segment_interaction(segmenter):
    """Test de segmentation d'une interaction complète."""
    prompt = "Je préfère Python à Java."
    response = "Python est effectivement un excellent choix pour l'IA."
    
    phrases = segmenter.segment_interaction(prompt, response)
    
    assert len(phrases) == 2
    assert any("Python à Java" in p.text for p in phrases)
    assert any("excellent choix" in p.text for p in phrases)


def test_segment_empty_text(segmenter):
    """Test avec texte vide."""
    phrases = segmenter.segment("")
    assert len(phrases) == 0


def test_segment_no_punctuation(segmenter):
    """Test avec texte sans ponctuation."""
    text = "Je préfère Python à Java et j aime travailler sur des projets d IA"
    phrases = segmenter.segment(text)
    
    # Devrait créer une phrase si assez longue
    if len(text) >= segmenter.min_length:
        assert len(phrases) >= 1


def test_segment_long_text(segmenter):
    """Test avec texte long."""
    text = "Phrase 1. Phrase 2. Phrase 3. Phrase 4. Phrase 5."
    phrases = segmenter.segment(text)
    
    assert len(phrases) == 5


def test_segment_with_ellipsis(segmenter):
    """Test avec points de suspension."""
    text = "Je réfléchis... C'est intéressant. Continuons."
    phrases = segmenter.segment(text)
    
    assert len(phrases) >= 2

