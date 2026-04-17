castellatedMesh true;
snap true;
addLayers false;

maxLocalCells 100000;
maxGlobalCells 2000000;
minRefinementCells 0;
maxLoadUnbalance 0.10;
nCellsBetweenLevels 2;

innerCylinderSurfaceRefinementLevel (3 3);
propellerTipSurfaceRefinementLevel (5 5);

outerCylinderRefinementRegionLevel ((1E15 2));
innerCylinderRefinementRegionMode distance;
innerCylinderRefinementRegionLevel ((0.02 3));
propellerTipRefinementRegionMode distance;
propellerTipRefinementRegionLevel ((0.002 5) (0.01 4) (0.03 3));

nSmoothPatch 3;
tolerance 1.0;
nSolveIter 30;
nRelaxIter 5;
nFeatureSnapIter 10;
implicitFeatureSnap true;
explicitFeatureSnap true;
multiRegionFeatureSnap true;


relativeSizes false;
propellerTipSurfaceLayers 2;
expansionRatio 1.15;
firstLayerThickness 0.00022;
minThickness 0.00005;
nGrow 0;
featureAngle 120;
addLayersnRelaxIter 5;
nSmoothSurfaceNormals 1;
nSmoothNormals 3;
nSmoothThickness 10;
maxFaceThicknessRatio 0.7;
maxThicknessToMedialRatio 0.5;
minMedialAxisAngle 90;
nLayerIter 100;
nBufferCellsNoExtrude 0;

maxNonOrtho 65;
maxBoundarySkewness 4;
maxInternalSkewness 4;
maxConcave 80;
minVol 1e-13;
mergeTolerance 1e-6;