from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from database import Base

class Conjunto(Base):
    __tablename__ = "conjuntos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, unique=True, nullable=False)

    subconjuntos = relationship("Subconjunto", back_populates="conjunto", cascade="all, delete")

class Subconjunto(Base):
    __tablename__ = "subconjuntos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True, nullable=False)
    conjunto_id = Column(Integer, ForeignKey("conjuntos.id"), nullable=False)

    conjunto = relationship("Conjunto", back_populates="subconjuntos")
    tareas_cotizadas = relationship("TareaCotizada", back_populates="subconjunto", cascade="all, delete")

class TareaCotizada(Base):
    __tablename__ = "tareas_cotizadas"

    id = Column(Integer, primary_key=True, index=True)
    codigo_articulo = Column(String, index=True, nullable=False)
    descripcion = Column(String)
    costo_unitario_sistema = Column(Float, nullable=True)
    fecha_costo = Column(String)
    precio_actualizado = Column(Float, nullable=True)
    costo_total = Column(Float, nullable=True)
    subconjunto_id = Column(Integer, ForeignKey("subconjuntos.id"), nullable=False)
    dolar_usado = Column(Float)
    inflacion_usada = Column(Float)
    fecha_calculo = Column(DateTime, default=datetime.datetime.utcnow)

    subconjunto = relationship("Subconjunto", back_populates="tareas_cotizadas")
