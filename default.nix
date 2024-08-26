{ python3Packages, ... }:

with python3Packages;
buildPythonPackage {
  pname = "owt";
  version = "0.1.0";
  pyproject = false;
  nativeBuildInputs = [];
  src = ./.;
  doCheck = true;
}
