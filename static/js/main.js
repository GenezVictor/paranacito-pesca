document.addEventListener("DOMContentLoaded", function () {

    const galerias = document.querySelectorAll(
        ".galeria"
    );

    galerias.forEach(function (galeria) {

        const imagenPrincipal =
            galeria.querySelector(
                ".imagen-principal"
            );

        const miniaturas = Array.from(
            galeria.querySelectorAll(
                ".miniatura"
            )
        );

        const anterior =
            galeria.querySelector(
                ".galeria-flecha.anterior"
            );

        const siguiente =
            galeria.querySelector(
                ".galeria-flecha.siguiente"
            );

        if (
            !imagenPrincipal ||
            miniaturas.length === 0
        ) {
            return;
        }

        let indiceActual = 0;


        function mostrarImagen(indice) {

            if (indice < 0) {
                indice = miniaturas.length - 1;
            }

            if (indice >= miniaturas.length) {
                indice = 0;
            }

            indiceActual = indice;

            const imagen =
                miniaturas[indice]
                    .querySelector("img");

            imagenPrincipal.style.opacity = "0";

            setTimeout(function () {

                imagenPrincipal.src =
                    imagen.src;

                imagenPrincipal.alt =
                    imagen.alt;

                imagenPrincipal.style.opacity = "1";

            }, 120);

            miniaturas.forEach(
                function (miniatura) {
                    miniatura.classList.remove(
                        "activa"
                    );
                }
            );

            miniaturas[indice]
                .classList.add("activa");
        }


        miniaturas.forEach(
            function (miniatura, indice) {

                miniatura.addEventListener(
                    "click",
                    function () {
                        mostrarImagen(indice);
                    }
                );

            }
        );


        if (anterior) {

            anterior.addEventListener(
                "click",
                function () {
                    mostrarImagen(
                        indiceActual - 1
                    );
                }
            );

        }


        if (siguiente) {

            siguiente.addEventListener(
                "click",
                function () {
                    mostrarImagen(
                        indiceActual + 1
                    );
                }
            );

        }

    });

});
