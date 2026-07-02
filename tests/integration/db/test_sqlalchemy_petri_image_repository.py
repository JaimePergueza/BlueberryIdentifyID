from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository


def test_add_get_and_list_by_sample(db_session):
    sample = SqlAlchemySampleRepository(db_session).add(Sample(sample_code="S-600"))
    repository = SqlAlchemyPetriImageRepository(db_session)
    petri_image = PetriImage(
        sample_id=sample.id,
        file_path="/storage/petri/a.jpg",
        file_name="a.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
        culture_medium="PDA",
    )

    created = repository.add(petri_image)
    fetched = repository.get_by_id(created.id)
    listed = repository.list_by_sample_id(sample.id)

    assert fetched is not None
    assert fetched.culture_medium == "PDA"
    assert len(listed) == 1
    assert listed[0].id == created.id
