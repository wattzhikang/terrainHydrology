BEGIN;

SELECT
    load_extension('mod_spatialite')
;

SELECT
    InitSpatialMetaData('None')
;

INSERT INTO
    spatial_ref_sys (
        srid, auth_name, auth_srid,
        ref_sys_name, proj4text, srtext
    )
VALUES
    (
        37008,
        'esri',
        37008,
        'Authalic sphere (ARC/INFO)',
        '+proj=longlat +ellps=sphere +no_defs +type=crs',
        'GEOGCRS[ ""GCS_Sphere_ARC_INFO "", DATUM[ ""D_Sphere_ARC_INFO "", ELLIPSOID[ ""Sphere_ARC_INFO "",6370997,0, LENGTHUNIT[ ""metre "",1]]], PRIMEM[ ""Greenwich "",0, ANGLEUNIT[ ""degree "",0.0174532925199433]], CS[ellipsoidal,2], AXIS[ ""geodetic latitude (Lat) "",north, ORDER[1], ANGLEUNIT[ ""degree "",0.0174532925199433]], AXIS[ ""geodetic longitude (Lon) "",east, ORDER[2], ANGLEUNIT[ ""degree "",0.0174532925199433]], USAGE[ SCOPE[ ""Not known. ""], AREA[ ""World. ""], BBOX[-90,-180,90,180]], ID[ ""ESRI "",37008]]'
    )
;

CREATE TABLE RiverNodes (
    id INT PRIMARY KEY
    ,parent INT
    ,elevation FLOAT
    ,inheritedwatershed FLOAT
    ,FOREIGN KEY (parent) REFERENCES RiverNodes(id)
);

SELECT
    AddGeometryColumn(
        'RiverNodes',
        'loc',
        37008,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Qs (
    id INT PRIMARY KEY
    ,elevation FLOAT
);

SELECT
    AddGeometryColumn(
        'Qs',
        'loc',
        37008,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Cells (
    rivernode INT
    ,q INT
    ,FOREIGN KEY (rivernode) REFERENCES RiverNodes(id)
    ,FOREIGN KEY (q) REFERENCES Qs(id)
);

CREATE TABLE Ts (
    id INT PRIMARY KEY
    ,rivercell INT
    ,elevation FLOAT
    ,FOREIGN KEY (rivercell) REFERENCES RiverNodes(id)
);

SELECT
    AddGeometryColumn(
        'Ts',
        'loc',
        37008,
        'POINT',
        'XY',
        1
    )
;

CREATE TABLE Edges (
    id INT PRIMARY KEY
    ,q1 INT
    ,q2 INT
    ,FOREIGN KEY (q1) REFERENCES Qs(id)
    ,FOREIGN KEY (q2) REFERENCES Qs(id)
);

CREATE TABLE Shoreline (
    edgeid INT
    ,FOREIGN KEY (edgeid) REFERENCES Edges(edgeid)
);

CREATE TABLE RiverPaths (
    id INT PRIMARY KEY
);

SELECT
    AddGeometryColumn(
        'RiverPaths',
        'path',
        37008,
        'LINESTRING',
        'XY',
        1
    )
;

COMMIT;