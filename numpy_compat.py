"""
numpy_compat.py
NumPy 2.0 compatibility patches for PsychoPy.
Import this module BEFORE any PsychoPy imports to avoid AttributeErrors.
"""
import numpy as np

if not hasattr(np, 'alltrue'):
    np.alltrue = np.all
if not hasattr(np, 'sometrue'):
    np.sometrue = np.any
if not hasattr(np, 'product'):
    np.product = np.prod
if not hasattr(np, 'cumproduct'):
    np.cumproduct = np.cumprod
if not hasattr(np, 'chararray'):
    np.chararray = np.char.chararray
