"""
Rotation utilities for 3D transformations.

Provides a subset of scipy.spatial.transform.Rotation functionality
without requiring scipy dependency.
"""

import numpy as np


class Rotation:
    """
    Rotation class supporting conversions between rotation vectors,
    rotation matrices, and quaternions.
    """

    def __init__(self, quat: np.ndarray) -> None:
        """Initialize rotation from quaternion [x, y, z, w]."""
        self._quat = np.asarray(quat, dtype=float)
        norm = np.linalg.norm(self._quat)
        if norm > 0:
            self._quat = self._quat / norm

    @classmethod
    def from_rotvec(cls, rotvec: np.ndarray) -> "Rotation":
        """
        Create rotation from rotation vector using Rodrigues' formula.

        Args:
            rotvec: Rotation vector [x, y, z] where magnitude is angle in radians

        Returns:
            Rotation instance
        """
        rotvec = np.asarray(rotvec, dtype=float)
        angle = np.linalg.norm(rotvec)

        if angle < 1e-8:
            quat = np.array([0.0, 0.0, 0.0, 1.0])
        else:
            axis = rotvec / angle
            half_angle = angle / 2.0
            sin_half = np.sin(half_angle)
            cos_half = np.cos(half_angle)
            quat = np.array([
                axis[0] * sin_half,
                axis[1] * sin_half,
                axis[2] * sin_half,
                cos_half
            ])

        return cls(quat)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> "Rotation":
        """
        Create rotation from 3x3 rotation matrix.

        Args:
            matrix: 3x3 rotation matrix

        Returns:
            Rotation instance
        """
        matrix = np.asarray(matrix, dtype=float)
        trace = np.trace(matrix)

        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2
            qw = 0.25 * s
            qx = (matrix[2, 1] - matrix[1, 2]) / s
            qy = (matrix[0, 2] - matrix[2, 0]) / s
            qz = (matrix[1, 0] - matrix[0, 1]) / s
        elif matrix[0, 0] > matrix[1, 1] and matrix[0, 0] > matrix[2, 2]:
            s = np.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2]) * 2
            qw = (matrix[2, 1] - matrix[1, 2]) / s
            qx = 0.25 * s
            qy = (matrix[0, 1] + matrix[1, 0]) / s
            qz = (matrix[0, 2] + matrix[2, 0]) / s
        elif matrix[1, 1] > matrix[2, 2]:
            s = np.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2]) * 2
            qw = (matrix[0, 2] - matrix[2, 0]) / s
            qx = (matrix[0, 1] + matrix[1, 0]) / s
            qy = 0.25 * s
            qz = (matrix[1, 2] + matrix[2, 1]) / s
        else:
            s = np.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1]) * 2
            qw = (matrix[1, 0] - matrix[0, 1]) / s
            qx = (matrix[0, 2] + matrix[2, 0]) / s
            qy = (matrix[1, 2] + matrix[2, 1]) / s
            qz = 0.25 * s

        quat = np.array([qx, qy, qz, qw])
        return cls(quat)

    @classmethod
    def from_quat(cls, quat: np.ndarray) -> "Rotation":
        """
        Create rotation from quaternion [x, y, z, w].

        Args:
            quat: Quaternion [x, y, z, w]

        Returns:
            Rotation instance
        """
        return cls(quat)

    def as_matrix(self) -> np.ndarray:
        """
        Convert rotation to 3x3 rotation matrix.

        Returns:
            3x3 rotation matrix
        """
        qx, qy, qz, qw = self._quat

        return np.array([
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
        ], dtype=float)

    def as_rotvec(self) -> np.ndarray:
        """
        Convert rotation to rotation vector.

        Returns:
            Rotation vector [x, y, z] where magnitude is angle in radians
        """
        qx, qy, qz, qw = self._quat

        if qw < 0:
            qx, qy, qz, qw = -qx, -qy, -qz, -qw

        angle = 2.0 * np.arccos(np.clip(abs(qw), 0.0, 1.0))
        sin_half_angle = np.sqrt(1.0 - qw * qw)

        if sin_half_angle < 1e-8:
            return 2.0 * np.array([qx, qy, qz])

        axis = np.array([qx, qy, qz]) / sin_half_angle
        return angle * axis

    def as_quat(self) -> np.ndarray:
        """
        Get quaternion representation.

        Returns:
            Quaternion [x, y, z, w]
        """
        return self._quat.copy()

    def apply(self, vectors: np.ndarray, inverse: bool = False) -> np.ndarray:
        """
        Apply this rotation to a set of vectors.

        Args:
            vectors: Array of shape (3,) or (N, 3)
            inverse: If True, apply the inverse rotation

        Returns:
            Rotated vectors
        """
        vectors = np.asarray(vectors, dtype=float)
        original_shape = vectors.shape

        if vectors.ndim == 1:
            if len(vectors) != 3:
                raise ValueError("Single vector must have length 3")
            vectors = vectors.reshape(1, 3)
            single_vector = True
        elif vectors.ndim == 2:
            if vectors.shape[1] != 3:
                raise ValueError("Vectors must have shape (N, 3)")
            single_vector = False
        else:
            raise ValueError("Vectors must be 1D or 2D array")

        rotation_matrix = self.as_matrix()

        if inverse:
            rotation_matrix = rotation_matrix.T

        rotated_vectors = vectors @ rotation_matrix.T

        if single_vector and original_shape == (3,):
            return rotated_vectors.flatten()

        return rotated_vectors

    def inv(self) -> "Rotation":
        """
        Invert this rotation.

        Returns:
            Rotation instance containing the inverse
        """
        qx, qy, qz, qw = self._quat
        inverse_quat = np.array([-qx, -qy, -qz, qw])
        return Rotation(inverse_quat)

    def __mul__(self, other: "Rotation") -> "Rotation":
        """
        Compose this rotation with another rotation.

        The composition `r2 * r1` means "apply r1 first, then r2".
        """
        if not isinstance(other, Rotation):
            return NotImplemented

        x1, y1, z1, w1 = other._quat
        x2, y2, z2, w2 = self._quat

        composed_quat = np.array([
            w2 * x1 + x2 * w1 + y2 * z1 - z2 * y1,
            w2 * y1 - x2 * z1 + y2 * w1 + z2 * x1,
            w2 * z1 + x2 * y1 - y2 * x1 + z2 * w1,
            w2 * w1 - x2 * x1 - y2 * y1 - z2 * z1,
        ])

        return Rotation(composed_quat)
