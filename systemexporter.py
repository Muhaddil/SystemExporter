# /// script
# dependencies = ["pymhf[gui]>=0.2.1"]
#
# [tool.pymhf]
# exe = "NMS.exe"
# steam_gameid = 275850
# start_paused = false
#
# [tool.pymhf.gui]
# always_on_top = true
#
# [tool.pymhf.logging]
# log_dir = "."
# log_level = "info"
# window_name_override = "System Data Exporter"
# ///
# -*- coding: utf-8 -*-
"""
NMS System Data Exporter v3.5
Corrección de enums internos
"""

import json
import logging
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import IntEnum

from pymhf import Mod
from pymhf.core.hooking import on_key_release
from pymhf.core.mod_loader import ModState
from pymhf.gui.decorators import BOOLEAN, STRING

import nmspy.data.types as nms
import nmspy.data.enums as enums

logger = logging.getLogger("SystemExporter")

RESOURCE_NAMES = {
    'RED2': 'Cadmio',
    'ASTEROID1': 'Plata',
    'ASTEROID2': 'Oro',
    'LAND1': 'Ferrita',
    'LAND2': 'Ferrita pura',
    'LAND3': 'Ferrita magnetizada',
    'FUEL1': 'Carbono',
    'FUEL2': 'Carbono condensado',
    'OXYGEN': 'Oxígeno',
    'CATALYST1': 'Sodio',
    'CATALYST2': 'Nitrato de sodio',
    'CAVE1': 'Cobalto',
    'CAVE2': 'Cobalto ionizado',
    'WATER1': 'Sal',
    'WATER2': 'Sal clorada',
    'LUSH1': 'Parafinio',
    'TOXIC1': 'Amonio',
    'COLD1': 'Dihidrógeno',
    'HOT1': 'Fósforo',
    'RADIO1': 'Uranio',
    'DUSTY1': 'Pirita',
    'SWAMP1': 'Hecesio',
    'LAVA1': 'Sulphurina',
    'YELLOW': 'Cobre',
    'YELLOW2': 'Cobre',
    'RED1': 'Cadmio',
    'GREEN1': 'Emerilio',
    'BLUE1': 'Indio',
    'GREEN2': 'Emerilio',
    'BLUE2': 'Indio',
    'EX_YELLOW': 'Cobre activado',
    'EX_RED': 'Cadmio activado',
    'EX_GREEN': 'Emerilio activado',
    'EX_BLUE': 'Indio activado',
    'GAS1': 'Nitrógeno',
    'GAS2': 'Azufre',
    'GAS3': 'Radón',
    'EX_PURPLE': 'Cuarcita activada',
    'PURPLE2': 'Cuarcita',
}

@dataclass
class ExporterState(ModState):
    total_exports: int = 0
    auto_export_enabled: bool = False
    debug_mode: bool = False


class SystemDataExporter(Mod):
    __author__ = ["Muhaddil"]
    __description__ = "System Data Exporter v3.5"
    __version__ = "3.5"
    
    state = ExporterState()
    
    def __init__(self):
        super().__init__()
        self.output_dir = Path("SystemData")
        self.output_dir.mkdir(exist_ok=True)
        self.solar_system_ptr = None
        
        logger.info("=" * 60)
        logger.info("Sistema de Exportacion v3.5 - Fix enums internos")
        logger.info("CONTROLES: U=Exportar, I=Consolidar, O=Auto-export")
        logger.info("           D=Debug system data")
        logger.info("=" * 60)
    
    def clean_bytes(self, value) -> Optional[str]:
        """Limpia bytes a string"""
        if value is None:
            return None
        try:
            if isinstance(value, bytes):
                return value.decode('utf-8', errors='ignore').strip('\x00').strip() or None
            if isinstance(value, str):
                if value.startswith("b'"):
                    value = value[2:-1]
                return value.strip('\x00').strip() or None
            if hasattr(value, 'value'):
                return self.clean_bytes(value.value)
            return str(value).strip() if value else None
        except:
            return None
    
    def translate_resource(self, res_id: str) -> str:
        """Traduce ID de recurso a nombre español"""
        if not res_id:
            return res_id
        clean_id = res_id.upper().strip()
        return RESOURCE_NAMES.get(clean_id, res_id)
    
    def extract_value(self, value, skip_object_expansion=False) -> Any:
        """Extrae valor de forma segura y recursiva"""
        try:
            type_str = str(type(value))
            if 'nmspy.data' in type_str and not skip_object_expansion:
                if 'GcSeed' in type_str:
                    return None
                
            if hasattr(value, 'name'):
                name = value.name
                if name.endswith('_'):
                    name = name[:-1]
                return name
            
            if isinstance(value, IntEnum):
                return value.name
            
            if isinstance(value, (int, float, bool)):
                return value
            
            if isinstance(value, (bytes, str)):
                return self.clean_bytes(value)
            
            if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
                return {
                    'x': float(value.x),
                    'y': float(value.y),
                    'z': float(value.z)
                }
            
            if hasattr(value, 'Seed') and not hasattr(value, '_fields_'):
                seed_val = value.Seed
                if isinstance(seed_val, int):
                    return seed_val
                return None
            
            return None
            
        except Exception as e:
            return None
    
    def safe_enum_extract(self, value, enum_type, field_name: str) -> Optional[Any]:
        """Extrae un enum de forma segura, manejando valores inválidos"""
        try:
            # Si ya es un enum válido
            if hasattr(value, 'name'):
                name = value.name
                if name.endswith('_'):
                    name = name[:-1]
                return name
            
            # Intentar convertir a int
            if hasattr(value, 'value'):
                int_val = int(value.value)
            else:
                int_val = int(value)
            
            # Verificar si está en rango válido para el enum
            try:
                enum_val = enum_type(int_val)
                return enum_val.name.rstrip('_')
            except (ValueError, KeyError):
                # Valor fuera de rango - loguear y devolver None
                logger.debug(f"{field_name}: valor {int_val} fuera de rango para {enum_type.__name__}")
                return None
                
        except Exception as e:
            logger.debug(f"Error extrayendo {field_name}: {e}")
            return None
    
    def extract_trading_data(self, trading_obj) -> Optional[Dict[str, Any]]:
        """Extrae datos de comercio correctamente"""
        try:
            result = {}
            
            # Wealth
            if hasattr(trading_obj, 'Wealth'):
                wealth = self.safe_enum_extract(
                    trading_obj.Wealth,
                    enums.cGcWealthClass,
                    'Wealth'
                )
                if wealth:
                    result['riqueza'] = wealth
            
            # TradingClass  
            if hasattr(trading_obj, 'TradingClass'):
                trading_class = self.safe_enum_extract(
                    trading_obj.TradingClass,
                    enums.cGcTradingClass,
                    'TradingClass'
                )
                if trading_class:
                    result['clase'] = trading_class
            
            # BuyBaseMarkup
            if hasattr(trading_obj, 'BuyBaseMarkup'):
                try:
                    markup = float(trading_obj.BuyBaseMarkup)
                    result['margen_compra'] = markup
                except:
                    pass
            
            # SellBaseMarkup
            if hasattr(trading_obj, 'SellBaseMarkup'):
                try:
                    markup = float(trading_obj.SellBaseMarkup)
                    result['margen_venta'] = markup
                except:
                    pass
            
            # BuyPriceIncreaseRate
            if hasattr(trading_obj, 'BuyPriceIncreaseRate'):
                try:
                    rate = float(trading_obj.BuyPriceIncreaseRate)
                    result['tasa_incremento_compra'] = rate
                except:
                    pass
            
            # SellPriceDecreaseRate
            if hasattr(trading_obj, 'SellPriceDecreaseRate'):
                try:
                    rate = float(trading_obj.SellPriceDecreaseRate)
                    result['tasa_decremento_venta'] = rate
                except:
                    pass
            
            # MaxBuyingPriceMultiplier
            if hasattr(trading_obj, 'MaxBuyingPriceMultiplier'):
                try:
                    mult = float(trading_obj.MaxBuyingPriceMultiplier)
                    result['multiplicador_maximo_compra'] = mult
                except:
                    pass
            
            # MinSellingPriceMultiplier
            if hasattr(trading_obj, 'MinSellingPriceMultiplier'):
                try:
                    mult = float(trading_obj.MinSellingPriceMultiplier)
                    result['multiplicador_minimo_venta'] = mult
                except:
                    pass
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error extrayendo TradingData: {e}")
            return None
    
    def extract_space_station_spawn(self, spawn_obj) -> Dict[str, Any]:
        """Extrae datos de SpaceStationSpawn correctamente"""
        try:
            result = {}
            
            # File (modelo de estación)
            if hasattr(spawn_obj, 'File'):
                file_str = self.clean_bytes(spawn_obj.File)
                if file_str:
                    result['archivo_modelo'] = file_str
            
            # Type - Es un enum interno de cGcSpaceStationSpawnData
            if hasattr(spawn_obj, 'Type'):
                try:
                    # Intentar obtener el nombre del enum directamente
                    if hasattr(spawn_obj.Type, 'name'):
                        type_name = spawn_obj.Type.name.rstrip('_')
                        result['tipo'] = type_name
                    else:
                        # Si no tiene name, intentar con el valor
                        type_val = int(spawn_obj.Type)
                        # Los tipos conocidos son: None, SpaceStation, MegaFreighter, DerelictFreighter
                        type_names = {0: 'None', 1: 'SpaceStation', 2: 'MegaFreighter', 3: 'DerelictFreighter'}
                        result['tipo'] = type_names.get(type_val, f'Unknown_{type_val}')
                except Exception as e:
                    logger.debug(f"Error extrayendo Type: {e}")
            
            # Race
            if hasattr(spawn_obj, 'Race'):
                race = self.safe_enum_extract(
                    spawn_obj.Race,
                    enums.eRace,
                    'SpaceStationSpawn.Race'
                )
                if race:
                    result['raza'] = race
            
            return result if result else {'presente': True}
            
        except Exception as e:
            logger.error(f"Error extrayendo SpaceStationSpawn: {e}")
            return {'presente': True}
    
    # =========================================================================
    # HOOKS
    # =========================================================================
    
    @nms.cGcSimulation.Update.after
    def on_update(self, this: ctypes._Pointer[nms.cGcSimulation], 
                  leMode: ctypes.c_uint32, lfTimeStep: float):
        try:
            sim = this.contents
            if hasattr(sim, 'mpSolarSystem') and sim.mpSolarSystem:
                if self.solar_system_ptr is None:
                    logger.info("Sistema capturado!")
                self.solar_system_ptr = sim.mpSolarSystem
        except:
            pass
    
    @nms.cGcSolarSystem.Construct.after
    def on_system_load(self, this: ctypes._Pointer[nms.cGcSolarSystem]):
        try:
            self.solar_system_ptr = this
            logger.info("Nuevo sistema cargado!")
            if self.state.auto_export_enabled:
                data = self.get_system_data()
                self.save_data(data)
        except Exception as e:
            logger.error(f"Error: {e}")
    
    # =========================================================================
    # GUI
    # =========================================================================
    
    @property
    @BOOLEAN("Auto-exportar:")
    def auto_export(self):
        return self.state.auto_export_enabled
    
    @auto_export.setter
    def auto_export(self, value):
        self.state.auto_export_enabled = value
    
    @property
    @STRING("Exports:", decimal=True)
    def exports(self):
        return str(self.state.total_exports)
    
    # =========================================================================
    # DEBUG
    # =========================================================================
    
    def log_system_structure(self):
        """Loguea la estructura completa de mSolarSystemData"""
        if not self.solar_system_ptr:
            logger.warning("No hay sistema cargado")
            return
        
        try:
            solar = self.solar_system_ptr.contents
            
            if hasattr(solar, 'mSolarSystemData'):
                ss = solar.mSolarSystemData
                logger.info("=" * 80)
                logger.info("ESTRUCTURA DE mSolarSystemData:")
                logger.info("=" * 80)
                
                attrs = [a for a in dir(ss) if not a.startswith('_')]
                logger.info(f"Atributos disponibles ({len(attrs)}):")
                for attr in sorted(attrs):
                    try:
                        value = getattr(ss, attr)
                        type_name = type(value).__name__
                        
                        if hasattr(value, 'name'):
                            display = f"{value.name} (enum)"
                        elif hasattr(value, 'value'):
                            display = f"{value.value}"
                        elif isinstance(value, (int, float, bool)):
                            display = str(value)
                        elif isinstance(value, bytes):
                            try:
                                decoded = value.decode('utf-8', errors='ignore').strip('\x00')
                                display = f'"{decoded}"' if decoded else "(vacío)"
                            except:
                                display = f"<bytes: {len(value)}>"
                        elif isinstance(value, str):
                            display = f'"{value}"' if value else "(vacío)"
                        else:
                            display = f"<{type_name}>"
                        
                        logger.info(f"  {attr:30s} = {display}")
                    except Exception as e:
                        logger.info(f"  {attr:30s} = ERROR: {e}")
                
                logger.info("=" * 80)
                
                # TradingData detallado
                if hasattr(ss, 'TradingData'):
                    logger.info("\nTRADINGDATA DETALLADO:")
                    td = ss.TradingData
                    td_attrs = [a for a in dir(td) if not a.startswith('_')]
                    for attr in sorted(td_attrs):
                        try:
                            value = getattr(td, attr)
                            if hasattr(value, 'name'):
                                logger.info(f"  {attr:35s} = {value.name}")
                            elif isinstance(value, (int, float)):
                                logger.info(f"  {attr:35s} = {value}")
                            elif isinstance(value, bool):
                                logger.info(f"  {attr:35s} = {value}")
                            else:
                                logger.info(f"  {attr:35s} = {type(value).__name__}")
                        except Exception as e:
                            logger.info(f"  {attr:35s} = ERROR: {e}")
                    logger.info("=" * 80)
                
                # SpaceStationSpawn detallado
                if hasattr(ss, 'SpaceStationSpawn'):
                    logger.info("\nSPACESTATIONSPAWN DETALLADO:")
                    sss = ss.SpaceStationSpawn
                    sss_attrs = [a for a in dir(sss) if not a.startswith('_')]
                    for attr in sorted(sss_attrs):
                        try:
                            value = getattr(sss, attr)
                            if hasattr(value, 'name'):
                                logger.info(f"  {attr:35s} = {value.name}")
                            elif isinstance(value, bytes):
                                decoded = value.decode('utf-8', errors='ignore').strip('\x00')
                                logger.info(f"  {attr:35s} = {decoded}")
                            else:
                                logger.info(f"  {attr:35s} = {value}")
                        except Exception as e:
                            logger.info(f"  {attr:35s} = ERROR: {e}")
                    logger.info("=" * 80)
                
        except Exception as e:
            logger.error(f"Error en log_system_structure: {e}")
    
    # =========================================================================
    # EXTRACCION
    # =========================================================================
    
    def get_system_data(self) -> Dict[str, Any]:
        data = {
            'timestamp': datetime.now().isoformat(),
            'version': '3.5',
            'sistema': {},
            'planetas': [],
        }
        
        if not self.solar_system_ptr:
            data['sistema']['error'] = 'Sin datos'
            return data
        
        try:
            solar = self.solar_system_ptr.contents
            
            if hasattr(solar, 'mSolarSystemData'):
                ss = solar.mSolarSystemData
                
                # Nombre
                if hasattr(ss, 'Name'):
                    name = self.clean_bytes(ss.Name)
                    if name:
                        data['sistema']['nombre'] = name
                
                # Raza
                if hasattr(ss, 'InhabitingRace'):
                    race = self.safe_enum_extract(
                        ss.InhabitingRace,
                        enums.cGcAlienRace,
                        'InhabitingRace'
                    )
                    if race:
                        data['sistema']['raza'] = race
                
                # Clase (con safe_enum_extract)
                if hasattr(ss, 'Class'):
                    class_val = self.safe_enum_extract(
                        ss.Class,
                        enums.cGcSolarSystemClass,
                        'Class'
                    )
                    if class_val:
                        data['sistema']['clase'] = class_val
                
                # StarType (con safe_enum_extract)
                if hasattr(ss, 'StarType'):
                    star_type = self.safe_enum_extract(
                        ss.StarType,
                        enums.cGcGalaxyStarTypes,
                        'StarType'
                    )
                    if star_type:
                        data['sistema']['tipo_estrella'] = star_type
                
                # Seed
                if hasattr(ss, 'Seed'):
                    try:
                        seed_obj = ss.Seed
                        if hasattr(seed_obj, 'Seed'):
                            seed_val = seed_obj.Seed
                            if isinstance(seed_val, int) and seed_val >= 0:
                                data['sistema']['seed'] = seed_val
                    except:
                        pass
                
                # SpaceStationSpawn - extraer correctamente
                if hasattr(ss, 'SpaceStationSpawn'):
                    station_data = self.extract_space_station_spawn(ss.SpaceStationSpawn)
                    if station_data:
                        data['sistema']['estacion_espacial'] = station_data
                
                # Otros campos seguros
                safe_fields = {
                    'AnomalyStation': 'estacion_anomalia',
                    'PirateStation': 'estacion_pirata',
                    'Abandoned': 'abandonado',
                    'Planets': 'num_planetas_campo',
                    'PrimePlanets': 'planetas_primarios',
                }
                
                for field, spanish_name in safe_fields.items():
                    if hasattr(ss, field):
                        try:
                            value = self.extract_value(getattr(ss, field))
                            if value is not None:
                                data['sistema'][spanish_name] = value
                        except:
                            pass
                
                # TradingData - extraer correctamente
                if hasattr(ss, 'TradingData'):
                    trading_data = self.extract_trading_data(ss.TradingData)
                    if trading_data:
                        data['sistema']['comercio'] = trading_data
                
                # ConflictData
                if hasattr(ss, 'ConflictData'):
                    conflict = self.safe_enum_extract(
                        ss.ConflictData,
                        enums.cGcPlayerConflictData,
                        'ConflictData'
                    )
                    if conflict:
                        data['sistema']['conflicto'] = conflict
                
                # AsteroidLevel - Intentar extraer sin especificar el enum anidado
                if hasattr(ss, 'AsteroidLevel'):
                    try:
                        # Intentar obtener el nombre directamente si es un enum
                        if hasattr(ss.AsteroidLevel, 'name'):
                            level_name = ss.AsteroidLevel.name.rstrip('_')
                            data['sistema']['nivel_asteroides'] = level_name
                        else:
                            # Si es un int, intentar mapear manualmente
                            level_val = int(ss.AsteroidLevel)
                            # Valores conocidos: 0=None, 1=LowCount, 2=HighCount, etc
                            level_names = {
                                0: 'None', 
                                1: 'LowCount', 
                                2: 'HighCount',
                                3: 'CommonRoids',
                                4: 'RareRoids'
                            }
                            if level_val in level_names:
                                data['sistema']['nivel_asteroides'] = level_names[level_val]
                    except Exception as e:
                        logger.debug(f"Error extrayendo AsteroidLevel: {e}")
            
            # Planetas - VALIDACIÓN ESTRICTA
            if hasattr(solar, 'maPlanets'):
                planets = solar.maPlanets
                valid_count = 0
                
                for i, planet in enumerate(planets):
                    if not self._is_valid_planet(planet):
                        continue
                    
                    planet_data = self.extract_planet(planet, valid_count)
                    data['planetas'].append(planet_data)
                    valid_count += 1
                
                data['sistema']['num_planetas'] = valid_count
                    
        except Exception as e:
            logger.error(f"Error: {e}")
            data['sistema']['error'] = str(e)
        
        return data
    
    def _is_valid_planet(self, planet) -> bool:
        """Verifica si un planeta tiene datos válidos con VALIDACIÓN ESTRICTA"""
        try:
            score = 0
            
            # CRITERIO 1: Nombre válido (3 puntos)
            if hasattr(planet, 'mPlanetData'):
                pd = planet.mPlanetData
                if hasattr(pd, 'Name'):
                    name = self.clean_bytes(pd.Name)
                    if name and len(name) > 0:
                        score += 3
            
            # CRITERIO 2: Seed válido (3 puntos)
            if hasattr(planet, 'mPlanetGenerationInputData'):
                gen = planet.mPlanetGenerationInputData
                if hasattr(gen, 'Seed'):
                    try:
                        seed_obj = gen.Seed
                        if hasattr(seed_obj, 'Seed'):
                            seed_val = seed_obj.Seed
                            if isinstance(seed_val, int) and seed_val not in (0, -1):
                                score += 3
                    except:
                        pass
                
                # CRITERIO 3: PlanetIndex válido (1 punto)
                if hasattr(gen, 'PlanetIndex'):
                    try:
                        idx = int(gen.PlanetIndex)
                        if 0 <= idx < 10:
                            score += 1
                    except:
                        pass
                
                # CRITERIO 4: Bioma válido (2 puntos)
                if hasattr(gen, 'Biome'):
                    biome = self.extract_value(gen.Biome)
                    if biome and biome not in ('Default', 'None', ''):
                        score += 2
            
            # CRITERIO 5: Posición razonable (1 punto)
            if hasattr(planet, 'mPosition'):
                pos = planet.mPosition
                x = abs(float(getattr(pos, 'x', 0)))
                y = abs(float(getattr(pos, 'y', 0)))
                z = abs(float(getattr(pos, 'z', 0)))
                if (x > 1000 or y > 1000 or z > 1000):
                    score += 1
            
            # CRITERIO 6: Tiene recursos (1 punto)
            if hasattr(planet, 'mPlanetData'):
                pd = planet.mPlanetData
                if hasattr(pd, 'CommonSubstanceID'):
                    res = self.clean_bytes(pd.CommonSubstanceID)
                    if res and len(res) > 0:
                        score += 1
            
            return score >= 6
            
        except Exception as e:
            logger.error(f"Error validando planeta: {e}")
            return False
    
    def extract_planet(self, planet, index: int) -> Dict[str, Any]:
        info = {'index': index}

        try:
            # Posición
            if hasattr(planet, 'mPosition'):
                pos = planet.mPosition
                info['posicion'] = {
                    'x': float(getattr(pos, 'x', 0)),
                    'y': float(getattr(pos, 'y', 0)),
                    'z': float(getattr(pos, 'z', 0)),
                }

            # PlanetData
            if hasattr(planet, 'mPlanetData'):
                pd = planet.mPlanetData

                # Nombre
                if hasattr(pd, 'Name'):
                    name = self.clean_bytes(pd.Name)
                    if name:
                        info['nombre'] = name

                # Vida
                if hasattr(pd, 'Life'):
                    life = self.extract_value(pd.Life)
                    if life:
                        info['vida'] = life

                # Fauna
                if hasattr(pd, 'CreatureLife'):
                    cl = self.extract_value(pd.CreatureLife)
                    if cl:
                        info['fauna'] = cl

                # Recursos básicos con traducción
                recursos_basicos = []
                recursos_basicos_trad = []
                for field in ('CommonSubstanceID', 'UncommonSubstanceID', 'RareSubstanceID'):
                    if hasattr(pd, field):
                        res = self.clean_bytes(getattr(pd, field))
                        if res and res not in recursos_basicos:
                            recursos_basicos.append(res)
                            recursos_basicos_trad.append(self.translate_resource(res))

                if recursos_basicos:
                    info['recursos_basicos'] = recursos_basicos
                    info['recursos_basicos_es'] = recursos_basicos_trad

                # Recursos extra
                recursos_extra = []
                recursos_extra_trad = []
                if hasattr(pd, 'ExtraResourceHints'):
                    try:
                        for hint in pd.ExtraResourceHints:
                            if not hint:
                                continue
                            if hasattr(hint, 'Resource'):
                                res = self.clean_bytes(hint.Resource)
                                if res and res not in recursos_extra:
                                    recursos_extra.append(res)
                                    recursos_extra_trad.append(self.translate_resource(res))
                    except:
                        pass

                if recursos_extra:
                    info['recursos_extra'] = recursos_extra
                    info['recursos_extra_es'] = recursos_extra_trad

            # GenerationInputData
            if hasattr(planet, 'mPlanetGenerationInputData'):
                gen = planet.mPlanetGenerationInputData
                gen_data = {}

                # Lista de campos a extraer
                gen_fields = {
                    'Biome': 'bioma',
                    'BiomeSubType': 'bioma_subtipo',
                    'Class': 'clase',
                    'CommonSubstance': 'sustancia_comun',
                    'RareSubstance': 'sustancia_rara',
                    'ForceContinents': 'forzar_continentes',
                    'HasRings': 'tiene_anillos',
                    'InAbandonedSystem': 'sistema_abandonado',
                    'InEmptySystem': 'sistema_vacio',
                    'InGasGiantSystem': 'sistema_gigante_gaseoso',
                    'InPirateSystem': 'sistema_pirata',
                    'PlanetIndex': 'indice_planeta',
                    'PlanetSize': 'tamaño_planeta',
                    'Prime': 'planeta_primario',
                    'RealityIndex': 'indice_realidad',
                    'Star': 'estrella',
                }

                for field, spanish_name in gen_fields.items():
                    if hasattr(gen, field):
                        try:
                            value = self.extract_value(getattr(gen, field))
                            if value is not None:
                                gen_data[spanish_name] = value
                                
                                # Traducir recursos
                                if 'sustancia' in spanish_name.lower() and isinstance(value, str):
                                    gen_data[f'{spanish_name}_es'] = self.translate_resource(value)
                        except:
                            pass

                # Seed
                if hasattr(gen, 'Seed'):
                    try:
                        seed_obj = gen.Seed
                        if hasattr(seed_obj, 'Seed'):
                            seed_val = seed_obj.Seed
                            if isinstance(seed_val, int):
                                gen_data['seed'] = seed_val
                    except:
                        pass

                if gen_data:
                    info['generacion'] = gen_data

            # Discovery
            if hasattr(planet, 'mPlanetDiscoveryData'):
                disc = planet.mPlanetDiscoveryData
                if hasattr(disc, 'mUniverseAddress'):
                    info['direccion_universo'] = str(disc.mUniverseAddress)

        except Exception as e:
            info['error'] = str(e)
            logger.error(f"Error extrayendo planeta {index}: {e}")

        return info
    
    def save_data(self, data: Dict[str, Any]) -> bool:
        try:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            name = data.get('sistema', {}).get('nombre', '')
            if name:
                safe = "".join(c for c in name if c.isalnum() or c in "- _")[:20]
                filename = f"system_{safe}_{ts}.json"
            else:
                filename = f"system_{ts}.json"
            
            path = self.output_dir / filename
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Guardado: {filename}")
            
            latest = self.output_dir / "latest_system.json"
            with open(latest, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.state.total_exports += 1
            return True
        except Exception as e:
            logger.error(f"Error guardando: {e}")
            return False
    
    def export_all(self) -> Optional[str]:
        try:
            systems = []
            for f in sorted(self.output_dir.glob("system_*.json")):
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        systems.append(json.load(fp))
                except:
                    pass
            
            if not systems:
                return None
            
            path = self.output_dir / "all_systems.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha': datetime.now().isoformat(),
                    'total': len(systems),
                    'sistemas': systems
                }, f, indent=2, ensure_ascii=False, default=str)
            return str(path)
        except:
            return None
    
    # =========================================================================
    # CONTROLES
    # =========================================================================
    
    @on_key_release("u")
    def export_current(self):
        logger.info("=" * 50)
        if not self.solar_system_ptr:
            logger.warning("Sin sistema!")
            return
        
        data = self.get_system_data()
        if self.save_data(data):
            logger.info(f"OK! Planetas: {len(data.get('planetas', []))}")
        logger.info("=" * 50)
    
    @on_key_release("i")
    def export_consolidated(self):
        logger.info("=" * 50)
        path = self.export_all()
        logger.info(f"Consolidado: {path}" if path else "Sin datos")
        logger.info("=" * 50)
    
    @on_key_release("o")
    def toggle(self):
        self.auto_export = not self.auto_export
        logger.info(f"Auto-export: {'ON' if self.auto_export else 'OFF'}")
    
    @on_key_release("d")
    def debug_system(self):
        """Debug: muestra estructura completa del sistema"""
        self.log_system_structure()


def main():
    return SystemDataExporter()


if __name__ == "__main__":
    from pymhf import load_mod_file
    load_mod_file(__file__)