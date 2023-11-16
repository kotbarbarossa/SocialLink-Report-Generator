from sqlalchemy import Column, Integer, ForeignKey, BigInteger, MetaData
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class VKUser(Base):
    __tablename__ = 'vk_users'

    id = Column(Integer, primary_key=True, index=True)
    vk_user_id = Column(BigInteger, unique=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="vk_user")
    groups = relationship(
        "VKGroup", secondary="user_groups", back_populates="users")
