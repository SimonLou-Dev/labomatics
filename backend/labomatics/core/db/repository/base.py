"""Repository générique."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeMeta, selectinload

from labomatics.core.db.session import async_session_local

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


@dataclass
class Page(Generic[ModelType]):
    """Pagination."""

    items: Sequence[ModelType]  # Contenu de la page
    page: int  # Page courante
    per_page: int  # Taille d une page
    total: int  # Nombre total d éléments
    total_pages: int  # Nombre total de pages


class BaseRepository(Generic[ModelType]):
    """Repository générique fournissant les opérations CRUD usuelles."""

    def __init__(self, model: type[ModelType]) -> None:
        """Constructeur.

        Parameters
        ----------
        model : Type[ModelType]
            Modèle SQLAlchemy cible (ex: User).

        """
        self.model = model

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    async def get(
        self,
        m_id: UUID,
        relations: Iterable[str] | None = None,
    ) -> ModelType | None:
        """Récupère un enregistrement via son identifiant.

        Parameters
        ----------
        m_id : Any
            Identifiant primaire (UUID ou int selon ton modèle).
        relations : Iterable[str], optional
            Liste des relations à charger.

        Returns
        -------
        Optional[ModelType]
            L'objet si trouvé, sinon None.

        """
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.id == m_id)
            stmt = self._apply_relations(stmt, relations)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list(self, relations: Iterable[str] | None = None) -> Sequence[ModelType]:
        """Renvoie l'ensemble des objets du modèle.

        Parameters
        ----------
        relations : Iterable[str], optional
            Liste des relations à charger.

        Returns
        -------
        Sequence[ModelType]
            Liste des objets.

        """
        async with async_session_local() as session:
            stmt = select(self.model)
            stmt = self._apply_relations(stmt, relations)
            res = await session.execute(stmt)
            return res.scalars().all()

    async def add(self, instance: ModelType) -> ModelType:
        """Ajoute un nouvel objet en base.

        Parameters
        ----------
        instance : ModelType
            Instance SQLAlchemy à persister.

        Returns
        -------
        ModelType
            L'objet créé.

        Raises
        ------
        HTTPException :
            En cas de violation d'unicité ou autre erreur d'intégrité.

        """
        async with async_session_local() as session:
            session.add(instance)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(400, "Object already exists") from exc
            await session.refresh(instance)
            return instance

    async def delete(self, m_id: UUID) -> bool:
        """Supprime un objet via son identifiant.

        Parameters
        ----------
        m_id : Any
            Identifiant primaire.

        Returns
        -------
        bool
            True si supprimé, False si l'objet n'existait pas.

        """
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.id == m_id)
            result = await session.execute(stmt)
            obj = result.scalar_one_or_none()
            if not obj:
                return False

            await session.delete(obj)
            await session.commit()
            return True

    async def where(
        self,
        filters: Mapping[str, Any],
        relations: Iterable[str] | None = None,
    ) -> Sequence[ModelType]:
        """Retournes tous les objets selon des filtres.

        Parameters
        ----------
        filters :
            Colonnes SQLAlchemy en equality match.
        relations : Iterable[str], optional
            Liste des relations à charger.

        Returns
        -------
        Sequence[ModelType]
            Liste des correspondances

        """
        async with async_session_local() as session:
            stmt = select(self.model).filter_by(**filters)
            stmt = self._apply_relations(stmt, relations)
            res = await session.execute(stmt)
            return res.scalars().all()

    async def exists(
        self,
        filters: Mapping[str, Any],
        extra_filters: list[Any] | None = None,
    ) -> bool:
        """Vérifie l'existence d'un objet selon des filtres.

        Parameters
        ----------
        filters :
            Colonnes SQLAlchemy en equality match.
        extra_filters:
            Colonnes SQLAlchemy en where

        Returns
        -------
        bool
            True si un objet correspondant existe.

        """
        async with async_session_local() as session:
            stmt = select(self.model).filter_by(**filters).limit(1)
            if extra_filters:
                for cond in extra_filters:
                    stmt = stmt.where(cond)
            res = await session.execute(stmt)
            return res.scalar_one_or_none() is not None

    async def update(
        self,
        m_id: UUID,
        values: Mapping[str, Any],
    ) -> ModelType:
        """Met à jour un objet existant via son identifiant.

        Parameters
        ----------
        m_id : UUID
            Identifiant primaire de l'objet à mettre à jour.
        values : Mapping[str, Any]
            Clés/valeurs à modifier sur l'objet.

        Returns
        -------
        ModelType
            L'objet mis à jour.

        Raises
        ------
        HTTPException :
            Si l'objet n'existe pas.

        """
        async with async_session_local() as session:
            # Chargement
            stmt = select(self.model).where(self.model.id == m_id)
            res = await session.execute(stmt)
            instance = res.scalar_one_or_none()

            if instance is None:
                raise HTTPException(404, f"{self.model.__name__} not found")

            # Apply updates
            for field, value in values.items():
                setattr(instance, field, value)

            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(400, "Integrity error during update") from exc

            await session.refresh(instance)
            return instance

    # -------------------------------------------------------------------------
    # Méthodes avancées
    # -------------------------------------------------------------------------

    async def first_or_create(
        self,
        *,
        defaults: Mapping[str, Any] | None = None,
        filters: Mapping[str, Any],
    ) -> ModelType:
        """Récupère un objet correspondant aux filtres. Le crée s'il n'existe pas.

        Parameters
        ----------
        defaults : Optional[Mapping[str, Any]]
            Valeurs supplémentaires utilisées lors de la création.
        filters :
            Conditions de recherche (WHERE).

        Returns
        -------
        ModelType
            L'objet existant ou nouvellement créé.

        Raises
        ------
        HTTPException :
            Si une violation d'unicité survient.

        """
        async with async_session_local() as session:
            stmt = select(self.model).filter_by(**filters).limit(1)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance:
                return instance

            data = {**filters, **(defaults or {})}
            instance = self.model(**data)

            session.add(instance)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                stmt = select(self.model).filter_by(**filters).limit(1)
                return (await session.execute(stmt)).scalar_one()

            await session.refresh(instance)
            return instance

    async def update_or_create(
        self,
        *,
        defaults: Mapping[str, Any],
        filters: Mapping[str, Any],
    ) -> ModelType:
        """Met à jour un objet existant ou le crée s'il n'existe pas.

        Parameters
        ----------
        defaults : Mapping[str, Any]
            Champs à mettre à jour ou à utiliser lors de la création.
        filters :
            Critères identifiant l'objet.

        Returns
        -------
        ModelType
            L'objet mis à jour ou créé.

        """
        async with async_session_local() as session:
            stmt = select(self.model).filter_by(**filters).limit(1)
            result = await session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
                return instance

            data = {**filters, **defaults}
            instance = self.model(**data)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    # -------------------------------------------------------------------------
    # Pagination + Recherche
    # -------------------------------------------------------------------------

    async def paginate(
        self,
        *,
        filters: Mapping[str, Any],
        page: int = 1,
        per_page: int = 20,
        relations: Iterable[str] | None = None,
    ) -> Page[ModelType]:
        """Renvoie une page d'objets.

        Parameters
        ----------
        filters:
            Filtrage
        page : int
            Numéro de page (>= 1).
        per_page : int
            Nombre d'éléments par page.
        relations : Iterable[str], optional
            Liste des relations à charger.

        Returns
        -------
        Page[ModelType]
            La page

        """
        offset = (page - 1) * per_page

        async with async_session_local() as session:
            # Requête de base
            stmt = select(self.model)

            # Application des filtres simples (égalité)
            if filters:
                conditions = []
                for field, value in filters.items():
                    attr = getattr(self.model, field, None)
                    if attr is None:
                        raise ValueError(f"Champ inconnu dans le modèle: {field}")
                    conditions.append(attr == value)
                stmt = stmt.filter(*conditions)

            # Charger les relations
            stmt = self._apply_relations(stmt, relations)

            # Exécuter la requête paginée
            stmt_paginated = stmt.offset(offset).limit(per_page)
            result = await session.execute(stmt_paginated)
            items = result.scalars().all()

            # Compter le total d éléments correspondant aux filtres
            count_stmt = select(func.count()).select_from(self.model)

            if filters:
                for field, value in filters.items():
                    attr = getattr(self.model, field)
                    count_stmt = count_stmt.filter(attr == value)

            total = (await session.execute(count_stmt)).scalar_one()

            # Calculer le nombre total de pages
            total_pages = (total + per_page - 1) // per_page

            return Page(
                items=items,
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            )

    async def search(
        self,
        *,
        field: str,
        query: str,
        page: int = 1,
        per_page: int = 20,
        relations: Iterable[str] | None = None,
    ) -> Sequence[ModelType]:
        """Recherche textuelle simple sur un champ du modèle.

        Parameters
        ----------
        field : str
            Nom du champ sur lequel faire la recherche.
        query : str
            Texte recherché (LIKE).
        page : int
            Page de résultats.
        per_page : int
            Nombre par page.
        relations : Iterable[str], optional
            Liste des relations à charger.

        Returns
        -------
        Sequence[ModelType]
            Liste paginée des résultats.

        Raises
        ------
        AttributeError :
            Si le champ n'existe pas sur le modèle.

        """
        column = getattr(self.model, field, None)
        if column is None:
            msg = f"{self.model.__name__} has no field '{field}'"
            raise AttributeError(msg)

        offset = (page - 1) * per_page

        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(column.ilike(f"%{query}%"))
                .offset(offset)
                .limit(per_page)
            )
            stmt = self._apply_relations(stmt, relations)
            res = await session.execute(stmt)
            return res.scalars().all()

    # -------------------------------------------------------------------------
    # Loading des relations
    # -------------------------------------------------------------------------

    def _apply_relations(self, stmt: Select, relations: Iterable[str] | None) -> Select:
        if not relations:
            return stmt

        for path in relations:
            parts = path.split(".")
            attr = getattr(self.model, parts[0], None)
            if attr is None:
                msg = f"{self.model.__name__} has no relation '{parts[0]}'"
                raise AttributeError(msg)

            load_opt = selectinload(attr)
            current_model = attr.property.mapper.class_

            for sub in parts[1:]:
                sub_attr = getattr(current_model, sub, None)
                if sub_attr is None:
                    msg = f"{current_model.__name__} has no relation '{sub}'"
                    raise AttributeError(msg)
                load_opt = load_opt.selectinload(sub_attr)
                current_model = sub_attr.property.mapper.class_

            stmt = stmt.options(load_opt)

        return stmt
