(function () {
    const status = document.getElementById("passkey-status");
    const loginForm = document.getElementById("passkey-form");
    const enrollmentForm = document.getElementById("passkey-enrollment-form");

    function setStatus(message) {
        if (status) status.textContent = message;
    }

    function csrfToken(form) {
        return form.querySelector('input[name="csrfmiddlewaretoken"]').value;
    }

    function decodeBase64Url(value) {
        const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
        const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
        const binary = window.atob(padded);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
        }
        return bytes.buffer;
    }

    function encodeBase64Url(value) {
        const bytes = new Uint8Array(value);
        let binary = "";
        for (const byte of bytes) binary += String.fromCharCode(byte);
        return window.btoa(binary)
            .replace(/\+/g, "-")
            .replace(/\//g, "_")
            .replace(/=+$/g, "");
    }

    function decodeCredentialDescriptors(descriptors) {
        return (descriptors || []).map(function (descriptor) {
            return Object.assign({}, descriptor, { id: decodeBase64Url(descriptor.id) });
        });
    }

    function decodeCreationOptions(options) {
        const publicKey = Object.assign({}, options, {
            challenge: decodeBase64Url(options.challenge),
            user: Object.assign({}, options.user, { id: decodeBase64Url(options.user.id) }),
            excludeCredentials: decodeCredentialDescriptors(options.excludeCredentials),
        });
        return publicKey;
    }

    function decodeRequestOptions(options) {
        return Object.assign({}, options, {
            challenge: decodeBase64Url(options.challenge),
            allowCredentials: decodeCredentialDescriptors(options.allowCredentials),
        });
    }

    function serializeCredential(credential, registration) {
        const response = credential.response;
        const encodedResponse = {
            clientDataJSON: encodeBase64Url(response.clientDataJSON),
        };

        if (registration) {
            encodedResponse.attestationObject = encodeBase64Url(response.attestationObject);
            if (typeof response.getTransports === "function") {
                encodedResponse.transports = response.getTransports();
            }
        } else {
            encodedResponse.authenticatorData = encodeBase64Url(response.authenticatorData);
            encodedResponse.signature = encodeBase64Url(response.signature);
            encodedResponse.userHandle = response.userHandle
                ? encodeBase64Url(response.userHandle)
                : null;
        }

        return {
            id: credential.id,
            rawId: encodeBase64Url(credential.rawId),
            type: credential.type,
            response: encodedResponse,
            authenticatorAttachment: credential.authenticatorAttachment,
            clientExtensionResults: credential.getClientExtensionResults(),
        };
    }

    async function postJson(url, token, body) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": token,
            },
            body: JSON.stringify(body),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "The request could not be completed.");
        return result;
    }

    function supported() {
        return !!(window.PublicKeyCredential && navigator.credentials);
    }

    if (loginForm) {
        const button = document.getElementById("verify-passkey");
        const options = JSON.parse(document.getElementById("passkey-options").textContent);
        button.addEventListener("click", async function () {
            if (!supported()) {
                setStatus("This browser does not support passkeys. Try an up-to-date browser on your phone.");
                return;
            }
            button.disabled = true;
            setStatus("Waiting for device verification...");
            try {
                const credential = await navigator.credentials.get({
                    publicKey: decodeRequestOptions(options),
                });
                if (!credential) throw new Error("No passkey response was received.");
                const result = await postJson(
                    loginForm.dataset.completeUrl,
                    csrfToken(loginForm),
                    serializeCredential(credential, false)
                );
                window.location.assign(result.redirect);
            } catch (error) {
                setStatus(error.message || "Passkey verification failed. Sign in again to retry.");
                button.disabled = false;
            }
        });
    }

    if (enrollmentForm) {
        const prepareButton = document.getElementById("prepare-passkey");
        const createButton = document.getElementById("create-passkey");
        let creationOptions = null;

        enrollmentForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (!supported()) {
                setStatus("This browser does not support passkeys. Try an up-to-date browser on your phone.");
                return;
            }
            prepareButton.disabled = true;
            setStatus("Validating the one-time setup code...");
            try {
                const result = await postJson(
                    enrollmentForm.dataset.optionsUrl,
                    csrfToken(enrollmentForm),
                    {
                        username: enrollmentForm.elements.username.value,
                        setup_code: enrollmentForm.elements.setup_code.value,
                    }
                );
                creationOptions = result.options;
                enrollmentForm.hidden = true;
                createButton.classList.remove("hidden");
                setStatus("Continue on this device to create your passkey.");
            } catch (error) {
                setStatus(error.message || "Passkey setup could not be started.");
                prepareButton.disabled = false;
            }
        });

        createButton.addEventListener("click", async function () {
            if (!creationOptions) return;
            createButton.disabled = true;
            setStatus("Follow your device's prompt to create the passkey...");
            try {
                const credential = await navigator.credentials.create({
                    publicKey: decodeCreationOptions(creationOptions),
                });
                if (!credential) throw new Error("No passkey response was received.");
                const result = await postJson(
                    enrollmentForm.dataset.completeUrl,
                    csrfToken(enrollmentForm),
                    {
                        credential: serializeCredential(credential, true),
                        device_name: enrollmentForm.elements.device_name.value,
                    }
                );
                setStatus("Passkey registered. Redirecting to login...");
                window.location.assign(result.redirect);
            } catch (error) {
                setStatus(error.message || "Passkey registration failed. Restart setup to try again.");
                createButton.disabled = false;
            }
        });
    }
})();
